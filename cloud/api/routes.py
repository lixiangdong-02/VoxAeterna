"""云端 API 路由 — 认证 / 订阅 / 试用 / 管理后台"""

import sys
import json
import logging
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from cloud.database import get_db
from cloud.schemas import requests as schemas
from cloud.services import auth, subscription
from cloud.models.orm import User, Subscription, TrialCount, PaymentOrder, UsageLog, Announcement, Session as SessionModel
from cloud.config import CloudSettings

_settings = CloudSettings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ========== 依赖 ==========

async def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="未登录或 token 已过期")
    user = auth.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或 token 已过期")
    return user


async def admin_required(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ========== 认证 ==========

@router.post("/auth/register")
async def register(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = auth.register_user(db, req)
        return {"message": "注册成功", "user_id": user.id, "email": user.email}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/auth/login")
async def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    result = auth.login_user(db, req.email, req.password, req.device_fingerprint)
    if not result:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    if result.get("error") == "email_not_verified":
        raise HTTPException(status_code=403, detail=result.get("message", "请先验证邮箱"))
    return result


@router.post("/auth/refresh")
async def refresh_token(req: schemas.RefreshRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sess = auth.create_session(db, user.id, req.device_fingerprint)
    token = auth.create_access_token(user.id, sess.token_jti)
    return schemas.TokenResponse(access_token=token, expires_in=auth.ACCESS_TOKEN_EXPIRE_DAYS * 86400)


@router.post("/auth/logout")
async def logout(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    if not token:
        return {"message": "ok"}
    payload = auth.decode_token(token)
    if payload:
        jti = payload.get("jti", "")
        auth.delete_current_session(db, jti)
    return {"message": "已登出"}


@router.post("/auth/send-verify-code")
async def send_verify_code(req: schemas.SendVerifyCodeRequest, db: Session = Depends(get_db)):
    """发送邮箱验证码"""
    if req.purpose == "register":
        # 检查邮箱是否已被注册并激活
        user = db.query(User).filter(User.email == req.email).first()
        if user and user.status == "active":
            raise HTTPException(status_code=409, detail="该邮箱已注册")
    elif req.purpose == "reset_password":
        # 检查邮箱是否存在
        user = db.query(User).filter(User.email == req.email).first()
        if not user:
            # 不暴露用户是否存在，统一返回成功
            return {"message": "如果该邮箱已注册，验证码将发送至您的邮箱", "sent": False}
        if user.status != "active":
            raise HTTPException(status_code=403, detail="该账户未激活，无法重置密码")

    result = auth.send_verify_email(db, req.email, req.purpose)
    if not result["sent"] and "cooldown" in result:
        raise HTTPException(status_code=429, detail=result["message"])
    return {"message": result["message"], "sent": result["sent"]}


@router.post("/auth/verify-email")
async def verify_email(req: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    """校验邮箱验证码"""
    ok, msg = auth.verify_email_code(db, req.email, req.code, "register")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@router.post("/auth/forgot-password")
async def forgot_password(req: schemas.SendVerifyCodeRequest, db: Session = Depends(get_db)):
    """发送密码重置验证码"""
    if req.purpose != "reset_password":
        req.purpose = "reset_password"
    return await send_verify_code(req, db)


@router.post("/auth/reset-password")
async def reset_password(req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """用验证码重置密码"""
    ok, msg = auth.reset_password(db, req.email, req.code, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}


@router.get("/auth/profile")
async def profile(user: User = Depends(current_user)):
    return schemas.UserProfile(id=user.id, email=user.email, username=user.username,
                               role=user.role, status=user.status, created_at=user.created_at)


@router.put("/auth/profile")
async def update_profile(req: schemas.UpdateProfileRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """更新个人信息（用户名）"""
    if req.username is not None:
        user.username = req.username
    db.commit()
    db.refresh(user)
    return schemas.UserProfile(id=user.id, email=user.email, username=user.username,
                               role=user.role, status=user.status, created_at=user.created_at)


@router.put("/auth/password")
async def change_password(req: schemas.ChangePasswordRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """修改密码"""
    if not auth.verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.password_hash = auth.hash_password(req.new_password)
    db.commit()
    return {"message": "密码修改成功"}


# ========== 订阅 ==========

@router.get("/subscription/status")
async def subscription_status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    result = subscription.get_subscription_status(db, user.id)
    # also include trial info
    trials = db.query(TrialCount).filter(TrialCount.user_id == user.id).all()
    trial_remaining = sum(t.remaining for t in trials) if trials else 0
    result["trial_remaining"] = trial_remaining
    return result


@router.post("/subscription/order")
async def create_payment_order(req: schemas.CreateOrderRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        result = subscription.create_order(db, user.id, req.plan)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscription/order/{order_id}")
async def get_order_status(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = db.query(PaymentOrder).filter(PaymentOrder.id == order_id, PaymentOrder.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {
        "order_id": order.id,
        "plan": order.plan,
        "amount": float(order.amount),
        "status": order.status,
        "qrcode_url": order.qrcode_url or "",
        "paid_at": str(order.paid_at) if order.paid_at else None,
    }


@router.get("/subscription/payment-history")
async def payment_history(page: int = Query(default=1, ge=1), user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(PaymentOrder).filter(PaymentOrder.user_id == user.id).order_by(PaymentOrder.created_at.desc())
    total = q.count()
    orders = q.offset((page - 1) * 20).limit(20).all()
    items = [schemas.PaymentHistoryItem(
        id=o.id, plan=o.plan, amount=float(o.amount), status=o.status,
        payjs_order_id=o.payjs_order_id or "", paid_at=o.paid_at, created_at=o.created_at,
    ) for o in orders]
    return {"items": [i.model_dump() for i in items], "total": total, "page": page}


@router.post("/subscription/callback")
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    """支付宝异步通知回调"""
    try:
        body = await request.body()
        form_str = body.decode("utf-8")
        from urllib.parse import parse_qs
        form_data = {k: v[0] for k, v in parse_qs(form_str).items()}
    except Exception:
        raise HTTPException(status_code=400, detail="无效的请求体")

    sign = form_data.pop("sign", "")
    sign_type = form_data.pop("sign_type", "RSA2")
    trade_status = form_data.get("trade_status", "")
    out_trade_no = form_data.get("out_trade_no", "")
    total_amount = form_data.get("total_amount", "")

    logger.info("[payment] 支付宝回调 out_trade_no=%s trade_status=%s", out_trade_no, trade_status)

    # 签名验证
    if _settings.alipay_public_key:
        if not subscription._alipay_verify_sign(form_data, sign):
            logger.warning("[payment] 支付宝签名验证失败 out_trade_no=%s", out_trade_no)
            raise HTTPException(status_code=403, detail="签名验证失败")

    order = db.query(PaymentOrder).filter(PaymentOrder.out_trade_no == out_trade_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if trade_status == "TRADE_SUCCESS":
        order.status = "paid"
        order.paid_at = datetime.utcnow()
        subscription.activate_subscription(db, order.user_id, order.plan)
        logger.info("[payment] 支付成功: user=%d plan=%s amount=%s", order.user_id, order.plan, total_amount)
    elif trade_status == "TRADE_CLOSED":
        order.status = "cancelled"

    db.commit()
    return {"message": "success"}  # 支付宝要求返回小写 success


# ========== 试用 ==========

@router.post("/trial/sync")
async def sync_trial(req: schemas.TrialSyncRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return subscription.sync_trial(db, user.id, req.device_fingerprint, req.remaining)


@router.post("/trial/consume")
async def consume_trial(req: schemas.TrialConsumeRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return subscription.consume_trial(db, user.id, req.device_fingerprint)


@router.get("/trial/status")
async def trial_status(device_fingerprint: str = Query(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    trial = subscription.get_trial(db, user.id, device_fingerprint) or subscription.init_trial(db, user.id, device_fingerprint)
    return {"remaining": trial.remaining, "total_used": trial.total_used}


# ========== 用量 ==========

@router.post("/usage/report")
async def report_usage(req: schemas.UsageLogRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(UsageLog(user_id=user.id, text_length=req.text_length, duration_seconds=req.duration_seconds, device=req.device))
    db.commit()
    return {"message": "ok"}


# ========== 用户 ==========

@router.get("/user/usage-stats")
async def usage_stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total = db.query(func.count(UsageLog.id)).filter(UsageLog.user_id == user.id).scalar() or 0
    total_duration = db.query(func.sum(UsageLog.duration_seconds)).filter(UsageLog.user_id == user.id).scalar() or 0
    month_count = db.query(func.count(UsageLog.id)).filter(
        UsageLog.user_id == user.id, UsageLog.created_at >= month_start
    ).scalar() or 0
    month_duration = db.query(func.sum(UsageLog.duration_seconds)).filter(
        UsageLog.user_id == user.id, UsageLog.created_at >= month_start
    ).scalar() or 0

    account_age_days = 0
    if user.created_at:
        account_age_days = (now - user.created_at).days

    return schemas.UsageStatsResponse(
        total_syntheses=total,
        total_duration=float(total_duration),
        month_syntheses=month_count,
        month_duration=float(month_duration),
        account_age_days=account_age_days,
    )


@router.get("/user/sessions")
async def list_sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sessions = db.query(SessionModel).filter(SessionModel.user_id == user.id).order_by(SessionModel.created_at.desc()).all()
    items = [schemas.SessionItem(
        id=s.id, device_fingerprint=s.device_fingerprint or "",
        created_at=s.created_at, is_current=False,
    ) for s in sessions]
    return {"items": [i.model_dump() for i in items], "total": len(items)}


@router.post("/user/sessions/revoke-all")
async def revoke_all_sessions(authorization: str = Header(default=""), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """登出所有其他设备（保留当前会话）"""
    current_jti = ""
    token = authorization.replace("Bearer ", "")
    if token:
        payload = auth.decode_token(token)
        if payload:
            current_jti = payload.get("jti", "")

    if current_jti:
        # Delete all sessions EXCEPT current one
        db.query(SessionModel).filter(
            SessionModel.user_id == user.id,
            SessionModel.token_jti != current_jti,
        ).delete()
    else:
        auth.delete_user_sessions(db, user.id)
    db.commit()
    return {"message": "已登出所有其他设备"}


@router.delete("/user/account")
async def delete_account(req: schemas.DeleteAccountRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """注销账户（需验证密码）"""
    if not auth.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")
    user.status = "disabled"
    auth.delete_user_sessions(db, user.id)
    db.commit()
    return {"message": "账户已注销"}


# ========== 公告 ==========

@router.get("/announcements")
async def list_announcements(db: Session = Depends(get_db)):
    anns = db.query(Announcement).filter(Announcement.is_active == 1).order_by(Announcement.created_at.desc()).limit(5).all()
    return [schemas.AnnouncementResponse(id=a.id, title=a.title, body=a.body, is_active=bool(a.is_active), created_at=a.created_at) for a in anns]


# ========== 管理后台 ==========

@router.get("/admin/stats")
async def admin_stats(_: User = Depends(admin_required), db: Session = Depends(get_db)):
    return schemas.AdminStatsResponse(
        total_users=db.query(User).filter(User.role == "user").count(),
        active_subscriptions=db.query(Subscription).filter(Subscription.status == "active").count(),
        total_synthesis_count=db.query(UsageLog).count(),
        pending_orders=db.query(PaymentOrder).filter(PaymentOrder.status == "pending").count(),
    )


@router.get("/admin/users")
async def admin_list_users(page: int = Query(default=1, ge=1), search: str = Query(default=""),
                          _: User = Depends(admin_required), db: Session = Depends(get_db)):
    q = db.query(User)
    if search:
        q = q.filter((User.email.contains(search)) | (User.username.contains(search)))
    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    items = []
    for u in users:
        sub = db.query(Subscription).filter(Subscription.user_id == u.id, Subscription.status == "active").first()
        # 聚合该用户所有设备的试用信息
        trial_rows = db.query(TrialCount).filter(TrialCount.user_id == u.id).all()
        trial_remaining = sum(t.remaining for t in trial_rows)
        items.append(schemas.UserListItem(
            id=u.id, email=u.email, username=u.username, role=u.role, status=u.status,
            subscription_plan=sub.plan if sub else None, subscription_status=sub.status if sub else None,
            trial_remaining=trial_remaining,
            created_at=u.created_at,
        ).model_dump())
    return {"items": items, "total": total, "page": page}


@router.put("/admin/users/{user_id}")
async def admin_update_user(user_id: int, req: schemas.AdminUserUpdateRequest,
                            _: User = Depends(admin_required), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if req.status:
        u.status = req.status
    if req.role:
        u.role = req.role
    db.commit()
    return {"message": "已更新"}


@router.post("/admin/subscriptions")
async def admin_create_subscription(req: schemas.AdminSubscriptionCreateRequest,
                                    _: User = Depends(admin_required), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == req.user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.query(Subscription).filter(Subscription.user_id == req.user_id, Subscription.status == "active").update({"status": "cancelled"})
    now = datetime.utcnow()
    days = req.duration_days or subscription.PLAN_DURATION.get(req.plan.value, 30)
    sub = Subscription(user_id=req.user_id, plan=req.plan.value, status="active", starts_at=now, expires_at=now + timedelta(days=days))
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"message": "已开通", "subscription_id": sub.id, "expires_at": str(sub.expires_at)}


@router.post("/admin/announcements")
async def admin_create_announcement(req: schemas.AnnouncementCreateRequest,
                                    _: User = Depends(admin_required), db: Session = Depends(get_db)):
    a = Announcement(title=req.title, body=req.body, is_active=int(req.is_active))
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"message": "公告已发布", "id": a.id}


@router.put("/admin/announcements/{ann_id}")
async def admin_update_announcement(ann_id: int, req: schemas.AnnouncementUpdateRequest,
                                    _: User = Depends(admin_required), db: Session = Depends(get_db)):
    a = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="公告不存在")
    if req.title is not None:
        a.title = req.title
    if req.body is not None:
        a.body = req.body
    if req.is_active is not None:
        a.is_active = int(req.is_active)
    db.commit()
    return {"message": "已更新"}



# ========== 版本更新 ==========

@router.get("/version/latest")
async def latest_version():
    """最新版本信息，Electron 端启动时检查"""
    import os
    return {
        "version": os.getenv("VOX_LATEST_VERSION", "0.0.0"),
        "download_url": os.getenv("VOX_LATEST_DOWNLOAD_URL", ""),
        "changelog": os.getenv("VOX_LATEST_CHANGELOG", ""),
        "force_update": os.getenv("VOX_FORCE_UPDATE", "false").lower() == "true",
    }

@router.get("/health")
async def health():
    return {"status": "ok", "service": "VoxAeterna Cloud"}

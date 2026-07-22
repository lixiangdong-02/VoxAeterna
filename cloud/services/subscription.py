"""订阅 & 试用次数服务"""

import uuid
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from cloud.models.orm import User, Subscription, TrialCount, PaymentOrder
from cloud.schemas.requests import PlanEnum
from cloud.config import CloudSettings

_settings = CloudSettings()
logger = logging.getLogger(__name__)

DEFAULT_TRIAL_COUNT = 3
TRIAL_PERIOD_DAYS = 14
PLAN_DURATION = {"monthly": 30, "yearly": 365, "lifetime": 36500}
PLAN_PRICE = {"monthly": 1990, "yearly": 21900, "lifetime": 69900}
PLAN_NAMES = {"monthly": "月租方案", "yearly": "年租方案", "lifetime": "买断方案"}


def _alipay_sign(params: dict) -> str:
    """支付宝 RSA2 签名"""
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Hash import SHA256

    raw = _alipay_get_sign_content(params)
    key = RSA.import_key(_settings.alipay_private_key)
    signer = PKCS1_v1_5.new(key)
    digest = SHA256.new(raw.encode("utf-8"))
    signature = base64.b64encode(signer.sign(digest)).decode("utf-8")
    return signature


def _alipay_verify_sign(params: dict, signature: str) -> bool:
    """支付宝签名验证"""
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Hash import SHA256

    raw = _alipay_get_sign_content(params)
    key = RSA.import_key(_settings.alipay_public_key)
    verifier = PKCS1_v1_5.new(key)
    digest = SHA256.new(raw.encode("utf-8"))
    return verifier.verify(digest, base64.b64decode(signature))


def _alipay_get_sign_content(params: dict) -> str:
    """拼接支付宝待签名字符串"""
    sorted_params = sorted(
        [(k, v) for k, v in params.items() if v != "" and v is not None and k not in ("sign", "sign_type")],
        key=lambda x: x[0]
    )
    return "&".join(f"{k}={v}" for k, v in sorted_params)


def get_active_subscription(db: Session, user_id: int) -> Optional[Subscription]:
    return db.query(Subscription).filter(
        Subscription.user_id == user_id, Subscription.status == "active"
    ).order_by(Subscription.expires_at.desc()).first()


def get_subscription_status(db: Session, user_id: int) -> dict:
    sub = get_active_subscription(db, user_id)
    if sub:
        return {"plan": sub.plan, "status": sub.status, "starts_at": sub.starts_at,
                "expires_at": sub.expires_at, "auto_renew": bool(sub.auto_renew),
                "subscription_id": sub.id}
    return {"plan": "free", "status": "active", "starts_at": None, "expires_at": None,
            "auto_renew": False, "subscription_id": None}


def create_order(db: Session, user_id: int, plan: PlanEnum) -> dict:
    plan_str = plan.value
    amount_cents = PLAN_PRICE.get(plan_str, 2900)
    order = PaymentOrder(user_id=user_id, plan=plan_str,
                         amount=amount_cents / 100, status="pending")
    db.add(order)
    db.flush()

    out_trade_no = f"VOX-{order.id}-{uuid.uuid4().hex[:8]}"
    order.out_trade_no = out_trade_no

    # 如果配置了支付宝，调用当面付预下单 API
    if _settings.alipay_app_id and _settings.alipay_private_key:
        try:
            import httpx
            from Crypto.PublicKey import RSA

            biz_content = {
                "out_trade_no": out_trade_no,
                "total_amount": f"{amount_cents / 100:.2f}",
                "subject": f"VoxAeterna {PLAN_NAMES.get(plan_str, plan_str)}",
                "body": f"VoxAeterna {PLAN_NAMES.get(plan_str, plan_str)}",
            }
            params = {
                "app_id": _settings.alipay_app_id,
                "method": "alipay.trade.precreate",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "notify_url": _settings.alipay_notify_url,
                "biz_content": json.dumps(biz_content, ensure_ascii=False),
            }
            params["sign"] = _alipay_sign(params)

            resp = httpx.post("https://openapi.alipay.com/gateway.do", data=params, timeout=15)
            result = resp.json()
            logger.info("[payment] 支付宝响应: %s", result)

            trade_resp = result.get("alipay_trade_precreate_response", {})
            if trade_resp.get("code") == "10000":
                order.payjs_order_id = trade_resp.get("out_trade_no", "")
                order.qrcode_url = trade_resp.get("qr_code", "")
                db.commit()
                return {
                    "order_id": order.id,
                    "plan": plan_str,
                    "amount": float(order.amount),
                    "qrcode_url": trade_resp.get("qr_code", ""),
                    "status": "pending",
                }
            else:
                order.status = "cancelled"
                db.commit()
                raise ValueError(trade_resp.get("sub_msg") or trade_resp.get("msg", "支付下单失败"))
        except Exception as e:
            logger.error("[payment] 支付宝下单异常: %s", e)
            order.status = "cancelled"
            db.commit()
            raise ValueError(f"支付服务异常: {e}")
    else:
        # 未配置支付宝：开发模式（订单 pending，二维码为空）
        order.payjs_order_id = out_trade_no
        order.qrcode_url = ""
        db.commit()
        logger.info("[payment] 开发模式，未配置支付宝。订单 %d 创建为 pending", order.id)
        return {
            "order_id": order.id,
            "plan": plan_str,
            "amount": float(order.amount),
            "qrcode_url": "",
            "status": "pending",
        }


def activate_subscription(db: Session, user_id: int, plan: str) -> Subscription:
    db.query(Subscription).filter(
        Subscription.user_id == user_id, Subscription.status == "active"
    ).update({"status": "cancelled"})
    now = datetime.utcnow()
    days = PLAN_DURATION.get(plan, 0)
    expires = now + timedelta(days=days)
    sub = Subscription(user_id=user_id, plan=plan, status="active", starts_at=now, expires_at=expires)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def get_trial(db: Session, user_id: int, device_fingerprint: str) -> Optional[TrialCount]:
    trial = db.query(TrialCount).filter(
        TrialCount.user_id == user_id, TrialCount.device_fingerprint == device_fingerprint
    ).first()
    if trial is None:
        logger.info(f"[trial] get_trial: user={user_id} device={device_fingerprint} → 未找到记录")
        return None
    logger.info(f"[trial] get_trial: user={user_id} remaining={trial.remaining} total_used={trial.total_used} period_start={trial.period_start_at}")
    if trial.period_start_at is not None:
        days_since = (datetime.utcnow() - trial.period_start_at).total_seconds() / 86400
        if days_since >= TRIAL_PERIOD_DAYS:
            trial.remaining = DEFAULT_TRIAL_COUNT
            trial.period_start_at = datetime.utcnow()
            db.commit()
            logger.info(f"[trial] 周期重置: user={user_id} → remaining={DEFAULT_TRIAL_COUNT}")
    return trial


def init_trial(db: Session, user_id: int, device_fingerprint: str) -> TrialCount:
    trial = TrialCount(user_id=user_id, device_fingerprint=device_fingerprint,
                       remaining=DEFAULT_TRIAL_COUNT, total_used=0,
                       period_start_at=datetime.utcnow())
    db.add(trial)
    db.commit()
    db.refresh(trial)
    return trial


def sync_trial(db: Session, user_id: int, device_fingerprint: str, remaining: int) -> dict:
    trial = get_trial(db, user_id, device_fingerprint) or init_trial(db, user_id, device_fingerprint)
    synced = min(trial.remaining, remaining)
    used = DEFAULT_TRIAL_COUNT - synced
    trial.remaining = synced
    trial.total_used = used if used > trial.total_used else trial.total_used
    db.commit()
    return {"remaining": trial.remaining, "total_used": trial.total_used, "synced": used <= trial.total_used}


def consume_trial(db: Session, user_id: int, device_fingerprint: str) -> dict:
    trial = get_trial(db, user_id, device_fingerprint) or init_trial(db, user_id, device_fingerprint)
    logger.info(f"[trial] consume_trial: user={user_id} remaining_before={trial.remaining} total_used={trial.total_used}")
    if trial.remaining <= 0:
        logger.info(f"[trial] consume_trial: user={user_id} 次数已用完，拒绝")
        return {"remaining": 0, "total_used": trial.total_used, "can_use": False}
    trial.remaining -= 1
    trial.total_used += 1
    db.commit()
    logger.info(f"[trial] consume_trial: user={user_id} remaining_after={trial.remaining} total_used={trial.total_used}")
    return {"remaining": trial.remaining, "total_used": trial.total_used, "can_use": True}

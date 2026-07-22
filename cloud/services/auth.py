"""认证服务 —— JWT 生成/验证、密码哈希、注册/登录、邮箱验证"""

import uuid
import random
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from cloud.models.orm import User as UserModel, Session as SessionModel, EmailVerification
from cloud.schemas.requests import RegisterRequest
from cloud.config import CloudSettings

_settings = CloudSettings()
logger = logging.getLogger(__name__)

SECRET_KEY = _settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, jti: str) -> str:
    import calendar
    now = datetime.utcnow()
    expire_dt = now + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "exp": calendar.timegm(expire_dt.timetuple()),
        "iat": calendar.timegm(now.timetuple()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(db: Session, token: str) -> Optional[UserModel]:
    payload = decode_token(token)
    if not payload:
        return None
    user_id = int(payload.get("sub", 0))
    jti = payload.get("jti", "")
    sess = db.query(SessionModel).filter(SessionModel.token_jti == jti).first()
    if not sess:
        return None
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def create_session(db: Session, user_id: int, device_fingerprint: str = "") -> SessionModel:
    jti = uuid.uuid4().hex
    expires = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    sess = SessionModel(user_id=user_id, device_fingerprint=device_fingerprint, token_jti=jti, expires_at=expires)
    db.add(sess)
    db.commit()
    return sess


def delete_user_sessions(db: Session, user_id: int) -> int:
    """删除用户所有会话，返回删除数量"""
    count = db.query(SessionModel).filter(SessionModel.user_id == user_id).delete()
    db.commit()
    return count


def delete_current_session(db: Session, token_jti: str) -> bool:
    """删除当前会话（登出）"""
    sess = db.query(SessionModel).filter(SessionModel.token_jti == token_jti).first()
    if sess:
        db.delete(sess)
        db.commit()
        return True
    return False


# ======================== 邮箱验证 ========================

def generate_verify_code() -> str:
    """生成 6 位随机数字验证码"""
    return f"{random.randint(0, 999999):06d}"


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """通过 SMTP 发送邮件"""
    if not _settings.smtp_user or not _settings.smtp_pass:
        logger.warning("[email] SMTP 未配置，跳过发送邮件: %s", to_email)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = _settings.smtp_from or _settings.smtp_user
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(_settings.smtp_host, _settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(_settings.smtp_user, _settings.smtp_pass)
            server.send_message(msg)
        logger.info("[email] 邮件发送成功: %s → %s", subject, to_email)
        return True
    except Exception as e:
        logger.error("[email] 邮件发送失败: %s", e)
        return False


def save_verification_code(db: Session, email: str, code: str, purpose: str) -> EmailVerification:
    """保存验证码到数据库，10 分钟过期"""
    # 废弃该邮箱同目的未使用的旧验证码
    db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.purpose == purpose,
        EmailVerification.used == 0,
    ).update({"used": 1})

    expires = datetime.utcnow() + timedelta(minutes=10)
    record = EmailVerification(email=email, code=code, purpose=purpose, expires_at=expires, used=0)
    db.add(record)
    db.commit()
    return record


def can_send_code(db: Session, email: str, purpose: str, cooldown_seconds: int = 60) -> bool:
    """检查是否可以发送验证码（冷却时间检查）"""
    cutoff = datetime.utcnow() - timedelta(seconds=cooldown_seconds)
    recent = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.purpose == purpose,
        EmailVerification.created_at >= cutoff,
    ).first()
    return recent is None


def send_verify_email(db: Session, email: str, purpose: str) -> dict:
    """发送邮箱验证码"""
    # 冷却时间检查
    if not can_send_code(db, email, purpose):
        remaining = 60
        cutoff = datetime.utcnow() - timedelta(seconds=60)
        recent = db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.purpose == purpose,
            EmailVerification.created_at >= cutoff,
        ).first()
        if recent:
            elapsed = (datetime.utcnow() - (recent.created_at or datetime.utcnow())).total_seconds()
            remaining = max(1, 60 - int(elapsed))
        return {"sent": False, "message": f"请 {remaining} 秒后再试", "cooldown": remaining}

    code = generate_verify_code()
    save_verification_code(db, email, code, purpose)

    if purpose == "register":
        subject = "VoxAeterna 邮箱验证码"
        html = f"""<div style="max-width:480px;margin:0 auto;padding:32px 24px;font-family:Arial,sans-serif">
<h2 style="color:#6366f1">VoxAeterna 邮箱验证</h2>
<p>您的验证码是：</p>
<h1 style="font-size:36px;letter-spacing:8px;color:#333;text-align:center;padding:16px;background:#f5f5ff;border-radius:8px">{code}</h1>
<p>验证码 10 分钟内有效。如非本人操作，请忽略此邮件。</p>
</div>"""
    else:
        subject = "VoxAeterna 密码重置"
        html = f"""<div style="max-width:480px;margin:0 auto;padding:32px 24px;font-family:Arial,sans-serif">
<h2 style="color:#6366f1">VoxAeterna 密码重置</h2>
<p>您正在重置密码，验证码是：</p>
<h1 style="font-size:36px;letter-spacing:8px;color:#333;text-align:center;padding:16px;background:#f5f5ff;border-radius:8px">{code}</h1>
<p>验证码 10 分钟内有效。如非本人操作，请忽略此邮件。</p>
</div>"""

    sent = _send_email(email, subject, html)
    if not sent:
        logger.info("[auth] SMTP 未配置，验证码（%s）: %s → %s", purpose, email, code)
    return {"sent": sent, "message": "验证码已发送" if sent else f"SMTP 未配置，开发模式验证码: {code}"}


def verify_email_code(db: Session, email: str, code: str, purpose: str) -> tuple[bool, str]:
    """校验邮箱验证码。返回 (成功, 消息)"""
    if purpose == "register":
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if not user:
            return False, "该邮箱未注册"

    record = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.purpose == purpose,
        EmailVerification.used == 0,
    ).order_by(EmailVerification.created_at.desc()).first()

    if not record:
        return False, "请先发送验证码"

    if record.expires_at and record.expires_at < datetime.utcnow():
        return False, "验证码已过期，请重新发送"

    if record.code != code:
        return False, "验证码错误"

    record.used = 1
    db.commit()

    if purpose == "register":
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if user:
            user.status = "active"
            db.commit()

    return True, "验证成功"


def register_user(db: Session, req: RegisterRequest) -> UserModel:
    existing = db.query(UserModel).filter(UserModel.email == req.email).first()
    if existing:
        raise ValueError("该邮箱已注册")
    user = UserModel(email=req.email, username=req.username, password_hash=hash_password(req.password),
                     status="pending", role="user")
    db.add(user)
    db.flush()
    from cloud.models.orm import Subscription
    db.add(Subscription(user_id=user.id, plan="free", status="active"))
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, email: str, password: str, device_fingerprint: str = "") -> Optional[dict]:
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    if user.status == "pending":
        return {"error": "email_not_verified", "message": "请先验证邮箱"}
    if user.status != "active":
        return None
    sess = create_session(db, user.id, device_fingerprint)
    token = create_access_token(user.id, sess.token_jti)
    return {
        "access_token": token, "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_DAYS * 86400,
        "user": {"id": user.id, "email": user.email, "username": user.username, "role": user.role},
    }


def reset_password(db: Session, email: str, code: str, new_password: str) -> tuple[bool, str]:
    """用验证码重置密码"""
    record = db.query(EmailVerification).filter(
        EmailVerification.email == email,
        EmailVerification.purpose == "reset_password",
        EmailVerification.used == 0,
    ).order_by(EmailVerification.created_at.desc()).first()

    if not record:
        return False, "请先发送验证码"
    if record.expires_at and record.expires_at < datetime.utcnow():
        return False, "验证码已过期，请重新发送"
    if record.code != code:
        return False, "验证码错误"

    record.used = 1
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        return False, "用户不存在"
    user.password_hash = hash_password(new_password)
    # 重置密码后强制登出所有设备
    delete_user_sessions(db, user.id)
    db.commit()
    return True, "密码重置成功"

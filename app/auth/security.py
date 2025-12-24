from passlib.context import CryptContext

passwordContext = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    return passwordContext.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return passwordContext.verify(password, password_hash)
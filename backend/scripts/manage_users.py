"""User management CLI for the IAPH RAG system.

Usage:
    uv run python -m scripts.manage_users create-user --username alice --password secret
    uv run python -m scripts.manage_users create-user \
        --username bob --password pass --profile-type investigador
    uv run python -m scripts.manage_users delete-user --username alice
    uv run python -m scripts.manage_users list-users
    uv run python -m scripts.manage_users add-profile-type --name administrador
    uv run python -m scripts.manage_users list-profile-types
"""

import argparse
import sys
import uuid

import bcrypt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.infrastructure.auth.models import UserModel, UserProfileTypeModel

engine = create_engine(settings.database_url_sync, echo=False)
SessionLocal = sessionmaker(bind=engine)


def create_user(args: argparse.Namespace) -> None:
    password_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt()).decode()

    with SessionLocal() as session:
        existing = session.execute(
            select(UserModel).where(UserModel.username == args.username)
        ).scalar_one_or_none()
        if existing:
            print(f"Error: user '{args.username}' already exists.")
            sys.exit(1)

        profile_type_id = None
        if args.profile_type:
            pt = session.execute(
                select(UserProfileTypeModel)
                .where(UserProfileTypeModel.name == args.profile_type)
            ).scalar_one_or_none()
            if pt is None:
                print(f"Error: profile type '{args.profile_type}' not found.")
                print("Available types:", ", ".join(list_profile_type_names(session)))
                sys.exit(1)
            profile_type_id = pt.id

        user = UserModel(
            id=uuid.uuid4(),
            username=args.username,
            password_hash=password_hash,
            profile_type_id=profile_type_id,
        )
        session.add(user)
        session.commit()
        print(f"User '{args.username}' created (id={user.id}).")


def delete_user(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        user = session.execute(
            select(UserModel).where(UserModel.username == args.username)
        ).scalar_one_or_none()
        if user is None:
            print(f"Error: user '{args.username}' not found.")
            sys.exit(1)
        session.delete(user)
        session.commit()
        print(f"User '{args.username}' deleted.")


def list_users(_args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        rows = session.execute(
            select(UserModel).order_by(UserModel.username)
        ).scalars().all()
        if not rows:
            print("No users found.")
            return
        print(f"{'Username':<20} {'Profile Type':<20} {'Created At':<25} {'ID'}")
        print("-" * 90)
        for u in rows:
            pt_name = u.profile_type.name if u.profile_type else "-"
            print(f"{u.username:<20} {pt_name:<20} {str(u.created_at):<25} {u.id}")


def add_profile_type(args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        existing = session.execute(
            select(UserProfileTypeModel)
            .where(UserProfileTypeModel.name == args.name)
        ).scalar_one_or_none()
        if existing:
            print(f"Profile type '{args.name}' already exists.")
            return
        pt = UserProfileTypeModel(id=uuid.uuid4(), name=args.name)
        session.add(pt)
        session.commit()
        print(f"Profile type '{args.name}' created (id={pt.id}).")


def list_profile_types(_args: argparse.Namespace) -> None:
    with SessionLocal() as session:
        names = list_profile_type_names(session)
        if not names:
            print("No profile types found.")
            return
        print("Profile types:")
        for name in names:
            print(f"  - {name}")


def list_profile_type_names(session) -> list[str]:
    rows = session.execute(
        select(UserProfileTypeModel).order_by(UserProfileTypeModel.name)
    ).scalars().all()
    return [r.name for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="IAPH RAG user management")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create-user", help="Create a new user")
    p_create.add_argument("--username", required=True)
    p_create.add_argument("--password", required=True)
    p_create.add_argument("--profile-type", default=None, help="Profile type name")
    p_create.set_defaults(func=create_user)

    p_delete = sub.add_parser("delete-user", help="Delete a user")
    p_delete.add_argument("--username", required=True)
    p_delete.set_defaults(func=delete_user)

    p_list = sub.add_parser("list-users", help="List all users")
    p_list.set_defaults(func=list_users)

    p_add_pt = sub.add_parser("add-profile-type", help="Add a new profile type")
    p_add_pt.add_argument("--name", required=True)
    p_add_pt.set_defaults(func=add_profile_type)

    p_list_pt = sub.add_parser("list-profile-types", help="List all profile types")
    p_list_pt.set_defaults(func=list_profile_types)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

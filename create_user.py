import os
import argparse
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'testproject.settings')
django.setup()

from django.contrib.auth import get_user_model  # NOQA
from django.contrib.auth.models import Permission  # NOQA
from django.contrib.contenttypes.models import ContentType  # NOQA

User = get_user_model()


def main():
    parser = argparse.ArgumentParser(description="Create sample user")
    parser.add_argument("-u", "--username", type=str, required=True,
                        help="Username to signin with")
    parser.add_argument("-e", "--email", type=str, required=False,
                        help="User's email")
    parser.add_argument("-p", "--password", type=str, required=True,
                        help="Password to signin with")

    args = parser.parse_args()
    create_user(args.username, args.password, email=args.email)


def create_user(username, password, email=None):

    user = User.objects.create_user(username, password=password, email=email)

    # Get the content type for the User model
    user_content_type = ContentType.objects.get_for_model(User)

    # Get the specific permissions you want to assign (view, change, etc.)
    view_permission = Permission.objects.get(codename='view_user',
                                             content_type=user_content_type)
    change_permission = Permission.objects.get(codename='change_user',
                                               content_type=user_content_type)

    # Assign permissions to the user instance
    user.user_permissions.add(view_permission, change_permission)
    user.save()


if __name__ == '__main__':
    main()

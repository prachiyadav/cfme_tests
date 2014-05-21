# -*- coding: utf-8 -*-

import cfme.configure.access_control as ac
from utils.update import update
import utils.error as error
import utils.randomness as random


def new_user():
    return ac.User(username='user' + random.generate_random_string(),
                   userid='uid' + random.generate_random_string(),
                   password='redhat',
                   password_verify='redhat',
                   email='xyz@redhat.com',
                   user_group_select='EvmGroup-user',
                   cost_center_select='Workload',
                   value_assign_select='Database')


def new_group():
    return ac.Group(description='grp' + random.generate_random_string(),
                    group_role_select='EvmRole-approver')


def new_role():
    return ac.Role(name='rol' + random.generate_random_string(),
                   vm_restriction_select='None')


#User test cases
def test_user_crud():
    user = new_user()
    user.create()
    with update(user):
        user.username = user.username + "edited"
    copied_user = user.copy()
    copied_user.delete()
    user.delete()


def test_user_duplicate_name():
    nu = new_user()
    nu.create()
    with error.expected("Userid has already been taken"):
        nu.create()
    nu.delete()


def test_username_required_error_validation():
    user = ac.User(
        username=None,
        userid='uid' + random.generate_random_string(),
        password='redhat',
        password_verify='redhat',
        email='xyz@redhat.com',
        user_group_select='EvmGroup-user')
    with error.expected("Name can't be blank"):
        user.create()


def test_userid_required_error_validation():
    user = ac.User(
        username='user' + random.generate_random_string(),
        userid=None,
        password='redhat',
        password_verify='redhat',
        email='xyz@redhat.com',
        user_group_select='EvmGroup-user')
    with error.expected("Userid can't be blank"):
        user.create()


def test_user_password_required_error_validation():
    user = ac.User(
        username='user' + random.generate_random_string(),
        userid='uid' + random.generate_random_string(),
        password=None,
        password_verify='redhat',
        email='xyz@redhat.com',
        user_group_select='EvmGroup-user')
    with error.expected("Password_digest can't be blank"):
        user.create()


def test_user_group_error_validation():
    user = ac.User(
        username='user' + random.generate_random_string(),
        userid='uid' + random.generate_random_string(),
        password='redhat',
        password_verify='redhat',
        email='xyz@redhat.com',
        user_group_select='<Choose a Group>')
    with error.expected("A User must be assigned to a Group"):
        user.create()


def test_user_email_error_validation():
    user = ac.User(
        username='user' + random.generate_random_string(),
        userid='uid' + random.generate_random_string(),
        password='redhat',
        password_verify='redhat',
        email='xyzdhat.com',
        user_group_select='EvmGroup-user')
    with error.expected("Email must be a valid email address"):
        user.create()


#Group test cases
def test_group_crud():
    group = new_group()
    group.create()
    with update(group):
        group.description = group.description + "edited"
    group.delete()


#Role test cases
def test_role_crud():
    role = new_role()
    role.create()
    with update(role):
        role.name = role.name + "edited"
    role.delete()
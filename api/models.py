from django.db import models
from django.contrib.auth.hashers import make_password, check_password


# =========================================================
# APP USER
# =========================================================

class AppUser(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255)   # was 10, too short for a hash

    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.email

class IPChangeRequest(models.Model):

    REQUEST_TYPES = [
        ("ADD", "Add"),
        ("EDIT", "Edit"),
        ("DELETE", "Delete"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    id = models.AutoField(primary_key=True)

    request_type = models.CharField(
        max_length=10,
        choices=REQUEST_TYPES
    )

    ip = models.CharField(max_length=50)

    isp = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    user_register = models.CharField(
        max_length=255
    )

    user_login = models.EmailField(
        max_length=255
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    admin_comment = models.TextField(
        blank=True,
        null=True
    )

    approved_by = models.EmailField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    approved_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.request_type} - {self.ip} - {self.status}"
    

# =========================================================
# IP REGISTER
# =========================================================

class IPRegister(models.Model):

    id = models.AutoField(
        primary_key=True
    )

    ip = models.CharField(
        max_length=50
    )

    isp = models.CharField(
        max_length=100
    )

    name = models.CharField(
        max_length=255
    )

    user_register = models.CharField(
        max_length=255
    )

    user_login = models.EmailField(
        max_length=255
    )

    # ID of uploaded Excel/document
    upload_id = models.IntegerField(
        null=True,
        blank=True
    )

    insert_date = models.DateTimeField(
        auto_now_add=True
    )

    update_date = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.ip


# =========================================================
# ISP
# =========================================================

class ISPForm(models.Model):

    id = models.AutoField(
        primary_key=True
    )

    isp = models.CharField(
        max_length=100
    )

    isp_lao_name = models.CharField(
        max_length=255
    )

    # ID of uploaded Excel/document
    upload_id = models.IntegerField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.isp


# =========================================================
# MEMBER
# =========================================================

class Member(models.Model):

    id = models.AutoField(
        primary_key=True
    )

    bnk_code = models.CharField(
        max_length=100
    )

    bnk_short_form = models.CharField(
        max_length=100
    )

    bnk_name = models.CharField(
        max_length=255
    )

    bnk_lao_name = models.CharField(
        max_length=255
    )

    # ID of uploaded Excel/document
    upload_id = models.IntegerField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.bnk_name


# =========================================================
# UPLOADED DOCUMENT
# =========================================================

class UploadedDocument(models.Model):

    id = models.AutoField(
        primary_key=True
    )

    file = models.FileField(
        upload_to="documents/"
    )

    original_name = models.CharField(
        max_length=255
    )

    uploaded_by = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    upload_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.original_name


# =========================================================
# DOCUMENT INFO
# =========================================================

class Documentinfo(models.Model):

    id = models.AutoField(
        primary_key=True
    )

    ip = models.CharField(
        max_length=50
    )

    isp = models.CharField(
        max_length=100
    )

    name = models.CharField(
        max_length=255
    )

    upload_id = models.IntegerField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name


    
import os
import pandas as pd

from django.db import transaction
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import (
    IPRegister,
    Member,
    ISPForm,
    UploadedDocument,
    Documentinfo,
    AppUser,
    IPChangeRequest
)

from .serializers import (
    IPRegisterSerializer,
    MemberSerializer,
    ISPFormSerializer,
    UploadedDocumentSerializer,
    DocumentinfoSerializer,
    AppUserSerializer,
    IPChangeRequestSerializer
)

# =========================================================
# APP USER LOGIN VIEW
# =========================================================

class LoginView(APIView):

    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"error": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = AppUser.objects.get(email__iexact=email)
        except AppUser.DoesNotExist:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check password hash
        if not user.check_password(password):
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {
                "message": "Login successful.",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "is_admin": user.is_admin
                }
            },
            status=status.HTTP_200_OK
        )

# =========================================================
# APP USER REGISTER & CHANGE PASSWORD
# =========================================================

class RegisterView(APIView):
    def post(self, request):
        data = request.data.copy()
        data["email"] = str(data.get("email", "")).strip().lower()

        serializer = AppUserSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "User registered successfully.",
                    "user": AppUserSerializer(user).data
                },
                status=status.HTTP_201_CREATED
            )

        # Turn the serializer errors into one readable "error" message
        first_field, messages = next(iter(serializer.errors.items()))
        return Response(
            {"error": f"{first_field}: {messages[0]}"},
            status=status.HTTP_400_BAD_REQUEST
        )


class ChangePasswordView(APIView):
    def post(self, request):
        email = request.data.get("email", "").strip()
        # Accept alternative keys if frontend sends 'password' or 'current_password'
        old_password = request.data.get("old_password") or request.data.get("current_password")
        new_password = request.data.get("new_password") or request.data.get("password", "")

        if not email or not new_password:
            return Response(
                {"error": "Email and new_password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = AppUser.objects.get(email__iexact=email)
        except AppUser.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate old_password ONLY if provided (for Change Password form)
        if old_password and not user.check_password(old_password):
            return Response(
                {"error": "Incorrect current password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {"error": "New password must be at least 6 characters long."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password updated successfully."},
            status=status.HTTP_200_OK
        )


# =========================================================
# IP CHANGE REQUESTS (NORMAL USERS & ADMIN)
# =========================================================

class IPChangeRequestListView(APIView):

    def get(self, request):
        requests = IPChangeRequest.objects.all().order_by("-created_at")
        serializer = IPChangeRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        email = data.get("user_login")

        if not email:
            return Response(
                {"error": "user_login is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = AppUser.objects.get(email=email)
        except AppUser.DoesNotExist:
            return Response(
                {"error": "User does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Admin applies changes directly without pending approval
        if user.is_admin:
            request_type = data.get("request_type")
            ip = data.get("ip")

            if request_type == "ADD":
                if IPRegister.objects.filter(ip__iexact=ip).exists():
                    return Response(
                        {"error": "IP address already exists"},
                        status=status.HTTP_409_CONFLICT
                    )

                IPRegister.objects.create(
                    ip=ip,
                    isp=data.get("isp", ""),
                    name=data.get("name", ""),
                    user_register=data.get("user_register", email),
                    user_login=email
                )

                return Response(
                    {"message": "IP added directly by admin"},
                    status=status.HTTP_201_CREATED
                )

        # Normal users create a pending request
        serializer = IPChangeRequestSerializer(data=data)

        if serializer.is_valid():
            serializer.save(status="PENDING")
            return Response(
                {
                    "message": "Request submitted successfully",
                    "request": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class IPChangeRequestApprovalView(APIView):

    def post(self, request, pk):
        admin_email = request.data.get("admin_email")
        action = request.data.get("action")
        comment = request.data.get("admin_comment", "")

        if not admin_email:
            return Response(
                {"error": "admin_email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            admin = AppUser.objects.get(email=admin_email)
        except AppUser.DoesNotExist:
            return Response(
                {"error": "Admin account not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not admin.is_admin:
            return Response(
                {"error": "You are not authorized as admin"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            change_request = IPChangeRequest.objects.get(id=pk)
        except IPChangeRequest.DoesNotExist:
            return Response(
                {"error": "Request not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if change_request.status != "PENDING":
            return Response(
                {"error": "This request has already been processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # REJECT REQUEST
        if action == "REJECT":
            change_request.status = "REJECTED"
            change_request.admin_comment = comment
            change_request.approved_by = admin_email
            change_request.approved_at = timezone.now()
            change_request.save()

            return Response({"message": "Request rejected"}, status=status.HTTP_200_OK)

        # APPROVE REQUEST
        if action == "APPROVE":
            with transaction.atomic():
                request_type = change_request.request_type

                if request_type == "ADD":
                    if IPRegister.objects.filter(ip__iexact=change_request.ip).exists():
                        return Response(
                            {"error": "IP address already exists"},
                            status=status.HTTP_409_CONFLICT
                        )

                    IPRegister.objects.create(
                        ip=change_request.ip,
                        isp=change_request.isp or "",
                        name=change_request.name or "",
                        user_register=change_request.user_register,
                        user_login=change_request.user_login
                    )

                elif request_type == "EDIT":
                    try:
                        ip_record = IPRegister.objects.get(ip__iexact=change_request.ip)
                    except IPRegister.DoesNotExist:
                        return Response(
                            {"error": "IP address not found"},
                            status=status.HTTP_404_NOT_FOUND
                        )

                    ip_record.isp = change_request.isp or ""
                    ip_record.name = change_request.name or ""
                    ip_record.update_date = timezone.now()
                    ip_record.save()

                elif request_type == "DELETE":
                    deleted, _ = IPRegister.objects.filter(ip__iexact=change_request.ip).delete()
                    if deleted == 0:
                        return Response(
                            {"error": "IP address not found"},
                            status=status.HTTP_404_NOT_FOUND
                        )

                change_request.status = "APPROVED"
                change_request.admin_comment = comment
                change_request.approved_by = admin_email
                change_request.approved_at = timezone.now()
                change_request.save()

            return Response({"message": "Request approved successfully"}, status=status.HTTP_200_OK)

        return Response(
            {"error": "Invalid action. Use APPROVE or REJECT."},
            status=status.HTTP_400_BAD_REQUEST
        )


# =========================================================
# HELPER FUNCTIONS FOR IMPORTING DATA
# =========================================================

def get_or_create_isp(isp_name, upload_id=None):
    isp_name = str(isp_name or "").strip()
    if not isp_name:
        return None, False

    existing_isp = ISPForm.objects.filter(isp__iexact=isp_name).first()
    if existing_isp:
        return existing_isp, False

    new_isp = ISPForm.objects.create(
        isp=isp_name,
        isp_lao_name=isp_name,
        upload_id=upload_id
    )
    return new_isp, True


def generate_member_code():
    number = 1
    while True:
        code = f"AUTO{number:03d}"
        if not Member.objects.filter(bnk_code=code).exists():
            return code
        number += 1


def get_or_create_member(member_name, upload_id=None):
    member_name = str(member_name or "").strip()
    if not member_name:
        return None, False

    existing_member = Member.objects.filter(bnk_short_form__iexact=member_name).first()
    if existing_member:
        return existing_member, False

    existing_member = Member.objects.filter(bnk_name__iexact=member_name).first()
    if existing_member:
        return existing_member, False

    new_member = Member.objects.create(
        bnk_code=generate_member_code(),
        bnk_short_form=member_name,
        bnk_name=member_name,
        bnk_lao_name=member_name,
        upload_id=upload_id
    )
    return new_member, True


def get_valid_email(email):
    email = str(email or "").strip()
    if not email:
        return "excelimport@example.com"
    try:
        validate_email(email)
        return email
    except ValidationError:
        return "excelimport@example.com"


# =========================================================
# IP REGISTER CRUD VIEWS
# =========================================================

class IPRegisterList(APIView):
    def get(self, request):
        records = IPRegister.objects.all().order_by("-insert_date")
        serializer = IPRegisterSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = IPRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IPRegisterDetail(APIView):
    def get(self, request, ip):
        try:
            record = IPRegister.objects.get(ip=ip)
        except IPRegister.DoesNotExist:
            return Response({"error": "IP address not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(IPRegisterSerializer(record).data, status=status.HTTP_200_OK)

    def put(self, request, ip):
        try:
            record = IPRegister.objects.get(ip=ip)
        except IPRegister.DoesNotExist:
            return Response({"error": "IP address not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = IPRegisterSerializer(record, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, ip):
        try:
            record = IPRegister.objects.get(ip=ip)
        except IPRegister.DoesNotExist:
            return Response({"error": "IP address not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = IPRegisterSerializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, ip):
        try:
            record = IPRegister.objects.get(ip=ip)
            record.delete()
            return Response({"message": "IP address deleted successfully."}, status=status.HTTP_200_OK)
        except IPRegister.DoesNotExist:
            return Response({"error": "IP address not found."}, status=status.HTTP_404_NOT_FOUND)


# =========================================================
# ISP & MEMBER VIEWS
# =========================================================

class IspList(APIView):
    def get(self, request):
        records = ISPForm.objects.all().order_by("isp")
        return Response(ISPFormSerializer(records, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ISPFormSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IspDetail(APIView):
    def get(self, request, pk):
        try:
            record = ISPForm.objects.get(pk=pk)
        except ISPForm.DoesNotExist:
            return Response({"error": "ISP not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ISPFormSerializer(record).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            record = ISPForm.objects.get(pk=pk)
            record.delete()
            return Response({"message": "ISP deleted successfully."}, status=status.HTTP_200_OK)
        except ISPForm.DoesNotExist:
            return Response({"error": "ISP not found."}, status=status.HTTP_404_NOT_FOUND)


class MemberList(APIView):
    def get(self, request):
        records = Member.objects.all().order_by("bnk_code")
        return Response(MemberSerializer(records, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MemberSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemberDetail(APIView):
    def get(self, request, pk):
        try:
            record = Member.objects.get(pk=pk)
        except Member.DoesNotExist:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MemberSerializer(record).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            record = Member.objects.get(pk=pk)
            record.delete()
            return Response({"message": "Member deleted successfully."}, status=status.HTTP_200_OK)
        except Member.DoesNotExist:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

# =========================================================
# DOCUMENT DETAIL
# =========================================================

class DocumentDetail(APIView):

    def get(self, request, pk):
        try:
            document = UploadedDocument.objects.get(pk=pk)
        except UploadedDocument.DoesNotExist:
            return Response(
                {"error": "Document not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = UploadedDocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            document = UploadedDocument.objects.get(pk=pk)
            document.delete()
            return Response(
                {"message": "Document deleted successfully."}, 
                status=status.HTTP_200_OK
            )
        except UploadedDocument.DoesNotExist:
            return Response(
                {"error": "Document not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )

# =========================================================
# DOCUMENT LIST & EXCEL/CSV FILE PARSER
# =========================================================

class DocumentList(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        documents = UploadedDocument.objects.all().order_by("-upload_date")
        return Response(UploadedDocumentSerializer(documents, many=True).data)

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        uploaded_by = request.data.get("uploaded_by", "Excel Import")

        if not uploaded_file:
            return Response({"error": "Please select a file."}, status=status.HTTP_400_BAD_REQUEST)

        max_size = 25 * 1024 * 1024
        if uploaded_file.size > max_size:
            return Response({"error": "File size cannot exceed 25MB."}, status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded_file.name
        extension = os.path.splitext(filename)[1].lower()

        allowed_extensions = [".xlsx", ".xls", ".csv", ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt"]
        if extension not in allowed_extensions:
            return Response(
                {"error": "This file type is not allowed.", "allowed": allowed_extensions},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Non-Excel file processing
        if extension not in [".xlsx", ".xls", ".csv"]:
            document = UploadedDocument.objects.create(
                file=uploaded_file,
                original_name=filename,
                uploaded_by=uploaded_by
            )
            return Response(
                {
                    "message": "File uploaded successfully.",
                    "document": UploadedDocumentSerializer(document).data
                },
                status=status.HTTP_201_CREATED
            )

        # Excel / CSV parsing
        try:
            df = pd.read_csv(uploaded_file) if extension == ".csv" else pd.read_excel(uploaded_file)
            df.columns = [str(col).strip().lower() for col in df.columns]

            required_columns = ["ip", "isp", "name"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                return Response(
                    {
                        "error": "Invalid Excel/CSV format.",
                        "missing_columns": missing_columns,
                        "required_columns": required_columns
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check for existing duplicate IPs across the system
            duplicate_ips = []
            for index, row in df.iterrows():
                ip = str(row["ip"]).strip()
                if not ip or ip.lower() == "nan":
                    continue

                existing_ip = IPRegister.objects.filter(ip__iexact=ip).first()
                if existing_ip:
                    duplicate_ips.append({
                        "row": index + 2,
                        "ip": ip,
                        "existing_information": {
                            "ip": existing_ip.ip,
                            "isp": existing_ip.isp,
                            "name": existing_ip.name
                        },
                        "uploaded_information": {
                            "ip": ip,
                            "isp": str(row["isp"]).strip(),
                            "name": str(row["name"]).strip()
                        }
                    })

            if duplicate_ips:
                return Response(
                    {
                        "error": "File cannot be uploaded because some IP addresses already exist in the database.",
                        "message": "No information was imported.",
                        "duplicate_count": len(duplicate_ips),
                        "duplicates": duplicate_ips
                    },
                    status=status.HTTP_409_CONFLICT
                )

            # Process valid file import
            document = UploadedDocument.objects.create(
                file=uploaded_file,
                original_name=filename,
                uploaded_by=uploaded_by
            )
            upload_id = document.id

            inserted_records, new_isps, new_members = [], [], []

            for index, row in df.iterrows():
                ip = str(row["ip"]).strip()
                isp = str(row["isp"]).strip()
                name = str(row["name"]).strip()

                if not ip or ip.lower() == "nan":
                    continue

                isp = "" if not isp or isp.lower() == "nan" else isp
                name = "" if not name or name.lower() == "nan" else name

                isp_obj, isp_created = get_or_create_isp(isp, upload_id=upload_id)
                if isp_created:
                    new_isps.append(isp)

                member_obj, member_created = get_or_create_member(name, upload_id=upload_id)
                if member_created:
                    new_members.append(name)

                Documentinfo.objects.create(
                    ip=ip,
                    isp=isp,
                    name=name,
                    upload_id=upload_id
                )

                IPRegister.objects.create(
                    ip=ip,
                    isp=isp,
                    name=name,
                    user_register=uploaded_by or "Excel Import",
                    user_login=get_valid_email(uploaded_by),
                    upload_id=upload_id
                )

                inserted_records.append({
                    "row": index + 2,
                    "ip": ip,
                    "isp": isp,
                    "name": name
                })

            return Response(
                {
                    "message": "File uploaded and imported successfully.",
                    "document": UploadedDocumentSerializer(document).data,
                    "upload_id": upload_id,
                    "inserted_rows": len(inserted_records),
                    "inserted_details": inserted_records,
                    "new_isp": new_isps,
                    "new_members": new_members
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to process file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        
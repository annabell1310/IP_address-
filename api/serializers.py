from rest_framework import serializers

from .models import (
    IPRegister,
    Member,
    ISPForm,
    UploadedDocument,
    Documentinfo,
    AppUser,
    IPChangeRequest
)


class AppUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8
    )

    class Meta:

        model = AppUser

        fields = [
            "id",
            "email",
            "password",
            "created_at"
        ]

        read_only_fields = [
            "id",
            "created_at"
        ]

    def create(self, validated_data):

        password = validated_data.pop(
            "password"
        )

        user = AppUser(
            **validated_data
        )

        user.set_password(
            password
        )

        user.save()

        return user

class IPChangeRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = IPChangeRequest
        fields = "__all__"
        read_only_fields = [
            "id",
            "status",
            "approved_by",
            "approved_at",
            "created_at",
        ]    


class IPRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = IPRegister
        fields = "__all__"


class MemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = Member
        fields = "__all__"


class ISPFormSerializer(serializers.ModelSerializer):

    class Meta:
        model = ISPForm
        fields = "__all__"


class UploadedDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = UploadedDocument
        fields = "__all__"


class DocumentinfoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Documentinfo
        fields = "__all__"
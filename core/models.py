from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=50, default="user")

    # umumiy XP (frontend va ranking uchun)
    xp = models.IntegerField(default=0)

    # frontenddan keladigan qo‘shimcha maydonlar
    university_short = models.CharField(
        max_length=255,
        blank=True,
        help_text="Qisqa nom: TATU, TSUE va hokazo",
    )
    university_full = models.CharField(
        max_length=255,
        blank=True,
        help_text="To‘liq nom: Toshkent Axborot Texnologiyalari Universiteti",
    )
    major = models.CharField(
        max_length=255,
        blank=True,
        help_text="Mutaxassislik / yo‘nalish",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.user.email


class Badge(models.Model):
    """
    Foydalanuvchining yutuqlari / badge’lari.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="badges",
    )
    title = models.CharField(max_length=200)

    # Har bir yutuq uchun XP miqdori
    xp_count = models.PositiveIntegerField(default=0)

    # kategoriya: international_cert, national_cert, activity...
    category = models.CharField(max_length=50, blank=True)

    # qo‘shimcha info (sub, level, note va h.k.)
    meta = models.JSONField(default=dict, blank=True)

    # isbot fayli (rasm / video / pdf ... )
    proof = models.FileField(
        upload_to="badges/proofs/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class Message(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    # frontend uchun matn
    text = models.TextField()
    attachment = models.FileField(upload_to="attachments/", blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    # o‘qilgan / o‘qilmagan
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"msg {self.id} from {self.from_user.email} to {self.to_user.email}"


class Resume(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resumes",
    )
    file = models.FileField(upload_to="resumes/")
    filename = models.CharField(max_length=512, blank=True)
    status = models.CharField(max_length=32, default="ready")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.filename or self.file.name

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AcademicYear(models.Model):
    name = models.CharField(max_length=20)
    is_active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_active:
            AcademicYear.objects.update(is_active=False)
        super().save(*args, **kwargs)

class Faculty(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Major(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="majors")
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('faculty', 'name') # Bir fakultetda bir xil nomli yo'nalish bo'lmasligi uchun

    def __str__(self):
        return f"{self.name}"


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

    # umumiy XP
    xp = models.IntegerField(default=0)
    global_rank = models.IntegerField(null=True, blank=True)

    # universitet
    university_short = models.CharField(max_length=255, blank=True)
    university_full = models.CharField(max_length=255, blank=True)

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles"
    )
    major = models.ForeignKey(
        Major,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles"
    )

    # bosqich (kurs)
    course = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        help_text="Bosqich (1–6)",
    )

    # guruh
    group = models.CharField(
        max_length=50,
        blank=True,
        help_text="Masalan: 23-05",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.user.email


class Badge(models.Model):
    CATEGORY_CHOICES = [
        ("international_cert", "International Certificate"),
        ("national_cert", "National Certificate"),
        ("intl_article", "International Article"),
        ("rep_article", "Republic Article"),
        ("activity", "Social activity"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="badges")

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)

    xp_count = models.IntegerField(default=0)

    proof = models.FileField(upload_to="achievements/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"



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



# IJTIMOIY FAOLLIK


class SocialAchievement(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlandi'),
        ('rejected', 'Rad etildi'),
    )

    # 11 ta asosiy yo'nalish (Nizom bo'yicha)
    CATEGORY_CHOICES = (
        (1, 'Kitobxonlik madaniyati'),
        (2, '5 muhim tashabbus'),
        (3, 'Akademik o\'zlashtirish (GPA)'),
        (4, 'Odob-axloq va dress-kod'),
        (5, 'Ko\'rik-tanlov va olimpiadalar'),
        (6, 'Darslardagi davomat'),
        (7, 'Ma\'rifat darslari'),
        (8, 'Volontyorlik va jamoat ishlari'),
        (9, 'Madaniy tashriflar'),
        (10, 'Sport va sog\'lom turmush'),
        (11, 'Boshqa ma\'naviy faollik'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_achievements')
    category = models.PositiveSmallIntegerField(choices=CATEGORY_CHOICES)
    sub_category = models.CharField(max_length=255, blank=True,
                                    null=True)  # Masalan: "Xalqaro" yoki "To'garak tashkil etish"
    rank = models.PositiveSmallIntegerField(blank=True, null=True)  # 1, 2, 3-o'rinlar

    date = models.DateField()
    description = models.TextField()
    proof_file = models.FileField(upload_to='social_proofs/')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    score = models.FloatField(default=0)  # Tasdiqlanganda avtomatik hisoblanadi
    admin_note = models.TextField(blank=True, null=True)  # Rad etilsa sababi yoziladi
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="achievements",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_category_display()}"


class AnnualRanking(models.Model):
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE
    )
    major = models.ForeignKey(
        Major,
        on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    total_score = models.FloatField()
    rank = models.IntegerField()

    is_grant_winner = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("academic_year", "major", "student")
        ordering = ["rank"]

    def __str__(self):
        return f"{self.student} - {self.rank}"

class GrantQuota(models.Model):
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE
    )
    major = models.ForeignKey(
        Major,
        on_delete=models.CASCADE
    )
    total_slots = models.IntegerField()

    def __str__(self):
        return f"{self.major} - {self.total_slots} grant"



class Scholarship(models.Model):

    CATEGORY_CHOICES = (
        ("state", "Davlat"),
        ("private", "Xususiy"),
        ("international", "Xalqaro"),
    )

    title = models.CharField(max_length=255)
    short_description = models.TextField()
    description = models.TextField()

    amount = models.CharField(max_length=100)

    organization = models.CharField(max_length=255)

    deadline = models.DateField()

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ScholarshipRequirement(models.Model):

    scholarship = models.ForeignKey(
        Scholarship,
        on_delete=models.CASCADE,
        related_name="requirements"
    )

    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text

class ScholarshipApplication(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    scholarship = models.ForeignKey(
        Scholarship,
        on_delete=models.CASCADE,
        related_name="applications"
    )

    motivation_letter = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=(
            ("pending","Pending"),
            ("approved","Approved"),
            ("rejected","Rejected")
        ),
        default="pending"
    )

    def __str__(self):
        return f"{self.user.username} - {self.scholarship.title}"


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    topic = models.CharField(max_length=100)

    short = models.TextField()
    description = models.TextField()

    image = models.ImageField(upload_to='announcements/', null=True, blank=True)

    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    views = models.IntegerField(default=0)

    type = models.CharField(max_length=50)
    is_important = models.BooleanField(default=False)

    locations = models.JSONField(default=list, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    benefits = models.JSONField(default=list, blank=True)

    link = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if isinstance(self.locations, str):
            self.locations = [i.strip() for i in self.locations.split(",")]

        if isinstance(self.requirements, str):
            self.requirements = [i.strip() for i in self.requirements.split(",")]

        if isinstance(self.benefits, str):
            self.benefits = [i.strip() for i in self.benefits.split(",")]

        super().save(*args, **kwargs)
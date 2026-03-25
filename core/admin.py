from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Profile, Message, Resume, Badge, Faculty, Major, SocialAchievement,
    AcademicYear, AnnualRanking, GrantQuota, Scholarship,
    ScholarshipRequirement, ScholarshipApplication, Announcement
)
from core.logic import calculate_score
from core.services.ranking import generate_annual_ranking
from django.contrib import messages
import openpyxl
from django.http import HttpResponse
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Avg
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from django import forms


# 1. Fakultetlarni admin panelga qo'shish
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

# 2. Yo'nalishlarni admin panelga qo'shish
@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ("id", "faculty", "name")
    list_filter = ("faculty",)
    search_fields = ("name", "faculty__name")

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "full_name",
        "university_short",
        "faculty", # Bu endi model ob'ektini ko'rsatadi
        "major",   # Bu ham
        "course",
        "group",
        "xp",
        "global_rank",
        "role",
        "created_at",
    )

    search_fields = (
        "full_name",
        "user__email",
        "phone",
        "university_short",
        "faculty__name", # ForeignKey bo'lgani uchun __name deb qidiramiz
        "major__name",   # Bu ham
        "group",
    )

    list_filter = (
        "role",
        "course",
        "faculty", # ForeignKey filtr sifatida yaxshi ishlaydi
        "university_short",
    )

    readonly_fields = ("created_at",)

    fieldsets = (
        (
            "Asosiy ma'lumotlar",
            {"fields": ("user", "full_name", "phone", "role", "avatar")},
        ),
        (
            "Ta'lim ma'lumotlari",
            {
                "fields": (
                    "university_short",
                    "university_full",
                    "faculty",
                    "major",
                    "course",
                    "group",
                )
            },
        ),
        ("Reyting / XP", {"fields": ("xp", "global_rank")}),
        ("Tizim", {"fields": ("created_at",)}),
    )

# Badge, Message va Resume o'zgarishsiz qoladi
@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "title", "xp_count", "created_at")
    search_fields = ("title", "user__username")
    list_filter = ("category",)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "from_user", "to_user", "created_at", "read")
    search_fields = ("from_user__email", "to_user__email", "text")
    list_filter = ("read",)

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "filename", "created_at")
    readonly_fields = ("created_at",)


# IJTIMOIY FAOLLIK


@admin.register(SocialAchievement)
class SocialAchievementAdmin(admin.ModelAdmin):
    # Ro'yxat ko'rinishi
    list_display = ('user', 'category_name', 'status', 'display_score', 'created_at')
    list_filter = ('status', 'category')

    # Talaba ma'lumotlarini admin o'zgartira olmasligi uchun readonly qilamiz
    readonly_fields = (
        'user', 'category', 'sub_category', 'rank', 'date',
        'description', 'display_proof_file', 'estimated_score'
    )

    # Admin faqat 'status', 'score' va 'admin_note' ni boshqara oladi
    fields = (
        'user', 'category', 'sub_category', 'rank', 'date',
        'description', 'display_proof_file', 'estimated_score',
        'status', 'admin_note'
    )

    def category_name(self, obj):
        return obj.get_category_display()

    category_name.short_description = "Yo'nalish"

    def display_score(self, obj):
        return f"{obj.score} ball"

    display_score.short_description = "Berilgan ball"

    def display_proof_file(self, obj):
        if obj.proof_file:
            if obj.proof_file.url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return format_html('<img src="{}" style="max-height: 300px; border-radius: 10px;" />',
                                   obj.proof_file.url)
            return format_html('<a href="{}" target="_blank">Hujjatni ko\'rish (PDF/Fayl)</a>', obj.proof_file.url)
        return "Fayl yuklanmagan"

    display_proof_file.short_description = "Isbot (Rasm/Hujjat)"

    def estimated_score(self, obj):
        score = calculate_score(obj)
        return format_html('<b style="color: #112d4e; font-size: 16px;">{} ball</b> (Nizom bo\'yicha)', score)

    estimated_score.short_description = "Tasdiqlansa beriladigan ball"

    # Tasdiqlash tugmasi (Action)
    actions = ['approve_selected', 'reject_selected']

    def approve_selected(self, request, queryset):
        for obj in queryset:
            if obj.status != 'approved':
                obj.score = calculate_score(obj)
                obj.status = 'approved'
                obj.save()
        self.message_user(request, "Tanlangan yutuqlar tasdiqlandi va ballar hisoblandi.")

    approve_selected.short_description = "✅ Tanlanganlarni tasdiqlash"

    def reject_selected(self, request, queryset):
        queryset.update(status='rejected', score=0)
        self.message_user(request, "Tanlangan yutuqlar rad etildi.")

    reject_selected.short_description = "❌ Tanlanganlarni rad etish"

    # Formani saqlashda ballni avtomat yozish
    def save_model(self, request, obj, form, change):
        if obj.status == 'approved' and obj.score == 0:
            obj.score = calculate_score(obj)
        elif obj.status == 'rejected':
            obj.score = 0
        super().save_model(request, obj, form, change)



def export_ranking_excel(modeladmin, request, queryset):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ranking"

    headers = [
        "Akademik Yil",
        "Yo'nalish",
        "Talaba",
        "Umumiy ball",
        "O'rin",
        "Grant g'olibi"
    ]

    ws.append(headers)

    for obj in queryset:
        ws.append([
            obj.academic_year.name,
            obj.major.name,
            obj.student.profile.full_name or obj.student.username,
            obj.total_score,
            obj.rank,
            "HA" if obj.is_grant_winner else "YO'Q"
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=ranking.xlsx"

    wb.save(response)
    return response

export_ranking_excel.short_description = "📥 Export selected to Excel"


def export_grant_winners_pdf(modeladmin, request, queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="grant_winners.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph("Grant Winners List", styles['Heading1']))
    elements.append(Spacer(1, 20))

    winners = queryset.filter(is_grant_winner=True)

    for obj in winners:
        text = f"{obj.student.profile.full_name} - {obj.major.name} - Rank {obj.rank}"
        elements.append(Paragraph(text, styles['Normal']))
        elements.append(Spacer(1, 10))

    doc.build(elements)

    return response


export_grant_winners_pdf.short_description = "📄 Export Grant Winners PDF"


@admin.register(AnnualRanking)
class AnnualRankingAdmin(admin.ModelAdmin):

    list_display = (
        "student_name",
        "major",
        "academic_year",
        "total_score",
        "colored_rank",
        "grant_status"
    )

    list_filter = (
        "academic_year",
        "major",
        "is_grant_winner"
    )

    search_fields = (
        "student__username",
        "student__email",
        "student__profile__full_name",
    )

    ordering = ("major", "rank")

    actions = [export_ranking_excel, export_grant_winners_pdf]

    readonly_fields = (
        "academic_year",
        "major",
        "student",
        "total_score",
        "rank",
        "is_grant_winner",
        "achievement_breakdown"
    )

    def student_name(self, obj):
        return obj.student.profile.full_name or obj.student.username
    student_name.short_description = "Talaba"

    def grant_status(self, obj):
        if obj.is_grant_winner:
            return format_html(
                '<span style="color:green;font-weight:bold;">🏆 GRANT</span>'
            )
        return format_html('<span style="color:gray;font-weight:bold;">Kontrakt</span>')
    grant_status.short_description = "Grant"

    def achievement_breakdown(self, obj):
        achievements = SocialAchievement.objects.filter(
            user=obj.student,
            academic_year=obj.academic_year,
            status='approved'
        )

        html = "<h3>Tasdiqlangan faolliklar</h3><ul>"

        for ach in achievements:
            html += f"<li>{ach.get_category_display()} — {ach.score} ball</li>"

        html += "</ul>"

        return format_html(html)

    achievement_breakdown.short_description = "Faolliklar haqida"

    def colored_rank(self, obj):
        if obj.rank == 1:
            return format_html('<span style="color:gold;font-size:18px;">🥇 1</span>')
        elif obj.rank == 2:
            return format_html('<span style="color:silver;font-size:18px;">🥈 2</span>')
        elif obj.rank == 3:
            return format_html('<span style="color:#cd7f32;font-size:18px;">🥉 3</span>')
        return obj.rank

    colored_rank.short_description = "Rank"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("statistics/", self.admin_site.admin_view(self.statistics_view), name="ranking-statistics"),
        ]
        return custom_urls + urls

    def statistics_view(self, request):
        from .models import AnnualRanking

        data = (
            AnnualRanking.objects
            .values("major__name")
            .annotate(avg_score=Avg("total_score"))
        )

        context = dict(
            self.admin_site.each_context(request),
            data=list(data),
        )

        return TemplateResponse(request, "admin/ranking_statistics.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["statistics_url"] = "statistics/"
        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(GrantQuota)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")

    actions = ["generate_ranking"]

    def generate_ranking(self, request, queryset):
        for year in queryset:
            generate_annual_ranking(year.id)

        self.message_user(
            request,
            "Reyting muvaffaqiyatli yaratildi!",
            messages.SUCCESS
        )

    generate_ranking.short_description = "Tanlangan yil uchun reytingni yaratish"



class RequirementInline(admin.TabularInline):
    model = ScholarshipRequirement
    extra = 1


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "organization",
        "amount",
        "deadline",
        "category"
    )

    inlines = [RequirementInline]


@admin.register(ScholarshipApplication)
class ApplicationAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "scholarship",
        "status",
        "created_at"
    )


class AnnouncementAdminForm(forms.ModelForm):
    # 🔥 SHU QISM ENG MUHIM
    locations = forms.CharField(required=False, widget=forms.Textarea, help_text="Vergul bilan ajrating: Samarqand — Cloud, Toshkent — AI")
    requirements = forms.CharField(required=False, widget=forms.Textarea, help_text="Vergul bilan ajrating: Yosh 18–30, Ingliz tili, Saralash asosida")
    benefits = forms.CharField(required=False, widget=forms.Textarea, help_text="Vergul bilan ajrating: Bepul ta’lim, Sertifikat, Ish imkoniyati")

    class Meta:
        model = Announcement
        fields = '__all__'

    # 🔥 CLEAN FUNKSIYALAR

    def clean_locations(self):
        data = self.cleaned_data.get("locations")
        if data:
            return [i.strip() for i in data.split(",")]
        return []

    def clean_requirements(self):
        data = self.cleaned_data.get("requirements")
        if data:
            return [i.strip() for i in data.split(",")]
        return []

    def clean_benefits(self):
        data = self.cleaned_data.get("benefits")
        if data:
            return [i.strip() for i in data.split(",")]
        return []

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementAdminForm
    list_display = ('title', 'type', 'views', 'created_at')
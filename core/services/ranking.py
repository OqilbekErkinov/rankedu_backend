from django.db.models import Sum, Q
from django.contrib.auth.models import User
from core.models import AnnualRanking, GrantQuota, Profile


def recalc_global_ranks():
    profiles = Profile.objects.all().order_by("-xp")

    for i, p in enumerate(profiles):
        p.global_rank = i + 1
        p.save(update_fields=["global_rank"])


def generate_annual_ranking(year_id):

    # Eski rankinglarni o‘chiramiz
    AnnualRanking.objects.filter(academic_year_id=year_id).delete()

    quotas = GrantQuota.objects.filter(academic_year_id=year_id)

    for quota in quotas:
        major = quota.major

        # 🔥 MUHIM JOY: profile__major
        students = (
            User.objects
            .filter(profile__major=major)
            .annotate(
                total_score=Sum(
                    'social_achievements__score',
                    filter=Q(
                        social_achievements__status='approved',
                        social_achievements__academic_year_id=year_id
                    )
                )
            )
            .order_by('-total_score')
        )

        position = 1

        for student in students:

            total = student.total_score or 0

            AnnualRanking.objects.create(
                academic_year_id=year_id,
                major=major,
                student=student,
                total_score=total,
                rank=position,
                is_grant_winner=position <= quota.total_slots
            )

            position += 1

    return "Ranking generated"
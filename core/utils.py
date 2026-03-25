from django.contrib.auth.models import User

def recalc_global_rank():
    users = User.objects.all().order_by("-profile__xp")

    for index, user in enumerate(users):
        user.profile.global_rank = index + 1
        user.profile.save()
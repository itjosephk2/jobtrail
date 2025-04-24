from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404, render, redirect
from django.forms import modelformset_factory

from .models import CV, ContactDetails, PersonalProfile, EducationItem, HackathonItem, ProjectSkill, Project, Job, SoftSkill
from .forms import (
    ContactDetailsForm, PersonalProfileForm, EducationFormSet, HackathonFormSet,
    ProjectFormSet, JobFormSet, SoftSkillFormSet
)

def generate_pdf(request):
    if settings.DEBUG:
        return HttpResponse(
            "PDF generation is disabled in development. This feature is available in production.",
            content_type="text/plain"
        )

    try:
        from weasyprint import HTML
    except ImportError:
        return HttpResponse(
            "WeasyPrint is not available. PDF generation failed.",
            content_type="text/plain"
        )

    template = get_template('create_pdf.html')
    context = {'name': 'John Doe', 'items': ['Item 1', 'Item 2']}
    html_content = template.render(context)
    pdf = HTML(string=html_content).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    return response

def create_cv(request):
    contact_details, _ = ContactDetails.objects.get_or_create(user=request.user)

    try:
        cv = CV.objects.get(user=request.user)
    except CV.DoesNotExist:
        cv = None

    if request.method == 'POST':
        contact_form = ContactDetailsForm(request.POST, instance=contact_details)
        profile_form = PersonalProfileForm(request.POST, instance=cv.personal_profile if cv else None)

        education_formset = EducationFormSet(request.POST, prefix='education')
        hackathon_formset = HackathonFormSet(request.POST, prefix='hackathon')
        project_formset = ProjectFormSet(request.POST, prefix='projects')
        job_formset = JobFormSet(request.POST, prefix='jobs')
        soft_skill_formset = SoftSkillFormSet(request.POST, prefix='softskills')

        if contact_form.is_valid() and profile_form.is_valid() and all(
            formset.is_valid() for formset in [
                education_formset, hackathon_formset, project_formset, job_formset, soft_skill_formset
            ]
        ):
            contact_details = contact_form.save(commit=False)
            contact_details.user = request.user
            contact_details.save()

            personal_profile = profile_form.save(commit=False)
            personal_profile.user = request.user
            personal_profile.save()

            if not cv:
                cv = CV.objects.create(
                    user=request.user,
                    contact_details=contact_details,
                    personal_profile=personal_profile
                )
            else:
                cv.contact_details = contact_details
                cv.personal_profile = personal_profile
                cv.save()

            for formset, related_field in zip(
                [education_formset, hackathon_formset, project_formset, job_formset, soft_skill_formset],
                [cv.education_items, cv.hackathon_items, cv.projects, cv.jobs, cv.soft_skills]
            ):
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.user = request.user
                    instance.save()
                    related_field.add(instance)

            return redirect('cv_detail', id=cv.id)
    else:
        contact_form = ContactDetailsForm(instance=contact_details)
        profile_form = PersonalProfileForm(instance=cv.personal_profile if cv else None)
        education_formset = EducationFormSet(queryset=EducationItem.objects.filter(user=request.user), prefix='education')
        hackathon_formset = HackathonFormSet(queryset=HackathonItem.objects.filter(user=request.user), prefix='hackathon')
        project_formset = ProjectFormSet(queryset=Project.objects.filter(user=request.user), prefix='projects')
        job_formset = JobFormSet(queryset=Job.objects.filter(user=request.user), prefix='jobs')
        soft_skill_formset = SoftSkillFormSet(queryset=SoftSkill.objects.filter(user=request.user), prefix='softskills')

    return render(request, 'create_cv.html', {
        'contact_form': contact_form,
        'profile_form': profile_form,
        'education_formset': education_formset,
        'hackathon_formset': hackathon_formset,
        'project_formset': project_formset,
        'job_formset': job_formset,
        'soft_skill_formset': soft_skill_formset,
    })

def cv_detail(request, id):
    cv = get_object_or_404(CV, id=id, user=request.user)
    return render(request, 'cv_detail.html', {'cv': cv})

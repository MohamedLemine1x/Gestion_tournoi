from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from organisateurs.utils.decorators import organisateur_required
from organisateurs.forms import MatchForm, ResultatMatchForm
from matchs.models import Match
from tournois.models import Tournoi
import logging

logger = logging.getLogger(__name__)

@login_required
@organisateur_required
def match_create(request):
    """
    Vue pour créer un nouveau match.
    """
    try:
        if request.method == 'POST':
            form = MatchForm(request.POST, organisateur=request.user.organisateur)
            if form.is_valid():
                match = form.save()
                logger.info(f"Match créé: {match}")
                messages.success(request, _("Le match a été créé avec succès."))
                return redirect('organisateurs:match_detail', pk=match.pk)
        else:
            form = MatchForm(organisateur=request.user.organisateur)

        return render(request, 'organisateurs/match_form.html', {
            'form': form,
            'action': _("Créer")
        })

    except Exception as e:
        logger.error(f"Erreur lors de la création du match: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de la création du match."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def match_edit(request, pk):
    """
    Vue pour modifier un match existant.
    """
    try:
        match = get_object_or_404(
            Match.objects.filter(tournoi__organisateur=request.user.organisateur),
            pk=pk
        )
        
        if request.method == 'POST':
            form = MatchForm(
                request.POST,
                instance=match,
                organisateur=request.user.organisateur
            )
            if form.is_valid():
                form.save()
                logger.info(f"Match modifié: {match}")
                messages.success(request, _("Le match a été modifié avec succès."))
                return redirect('organisateurs:match_detail', pk=match.pk)
        else:
            form = MatchForm(
                instance=match,
                organisateur=request.user.organisateur
            )

        return render(request, 'organisateurs/match_form.html', {
            'form': form,
            'match': match,
            'action': _("Modifier")
        })

    except Exception as e:
        logger.error(f"Erreur lors de la modification du match: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de la modification du match."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def match_detail(request, pk):
    """
    Vue pour afficher les détails d'un match.
    """
    try:
        match = get_object_or_404(
            Match.objects.filter(tournoi__organisateur=request.user.organisateur),
            pk=pk
        )

        context = {
            'match': match,
            'tournoi': match.tournoi,
            'equipe1': match.equipe1,
            'equipe2': match.equipe2,
        }
        return render(request, 'organisateurs/match_detail.html', context)

    except Exception as e:
        logger.error(f"Erreur lors de l'affichage du match: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de l'affichage du match."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def match_delete(request, pk):
    """
    Vue pour supprimer un match.
    """
    try:
        match = get_object_or_404(
            Match.objects.filter(tournoi__organisateur=request.user.organisateur),
            pk=pk
        )
        
        if request.method == 'POST':
            tournoi = match.tournoi
            match.delete()
            logger.info(f"Match supprimé du tournoi {tournoi}")
            messages.success(request, _("Le match a été supprimé avec succès."))
            return redirect('organisateurs:tournoi_detail', pk=tournoi.pk)

        return render(request, 'organisateurs/match_confirm_delete.html', {
            'match': match
        })

    except Exception as e:
        logger.error(f"Erreur lors de la suppression du match: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de la suppression du match."))
        return redirect('organisateurs:dashboard')

@login_required
@organisateur_required
def resultat_match(request, pk):
    """
    Vue pour saisir le résultat d'un match.
    """
    try:
        match = get_object_or_404(
            Match.objects.filter(tournoi__organisateur=request.user.organisateur),
            pk=pk
        )
        
        if request.method == 'POST':
            form = ResultatMatchForm(request.POST, instance=match)
            if form.is_valid():
                form.save()
                logger.info(f"Résultat du match mis à jour: {match}")
                messages.success(request, _("Le résultat du match a été enregistré avec succès."))
                return redirect('organisateurs:match_detail', pk=match.pk)
        else:
            form = ResultatMatchForm(instance=match)

        return render(request, 'organisateurs/resultat_match_form.html', {
            'form': form,
            'match': match
        })

    except Exception as e:
        logger.error(f"Erreur lors de la saisie du résultat: {str(e)}")
        messages.error(request, _("Une erreur est survenue lors de la saisie du résultat."))
        return redirect('organisateurs:dashboard') 
# matchs/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Match
from equipes.models import Equipe

def liste_matchs(request):
    """
    Vue pour afficher la liste de tous les matchs.
    """
    # Récupérer tous les matchs
    matchs = Match.objects.all().order_by('-date')
    
    # Séparer les matchs à venir et les matchs passés
    today = timezone.now()
    matchs_a_venir = matchs.filter(date__gt=today)
    matchs_passes = matchs.filter(date__lte=today)
    
    context = {
        'matchs_a_venir': matchs_a_venir,
        'matchs_passes': matchs_passes,
        'total_matchs': matchs.count()
    }
    
    return render(request, 'matchs/liste_matchs.html', context)

def detail_match(request, pk):
    """
    Vue pour afficher les détails d'un match.
    """
    match = get_object_or_404(Match, pk=pk)
    context = {
        'match': match,
        'now': timezone.now()
    }
    return render(request, 'matchs/detail_match.html', context)

@login_required
def creer_match(request):
    """
    Vue pour créer un nouveau match amical.
    Seuls les responsables d'équipe peuvent créer des matchs.
    """
    # Vérifier si l'utilisateur est un responsable
    if getattr(request.user, 'type', None) != 'responsable':
        messages.error(request, "Seuls les responsables d'équipe peuvent créer des matchs.")
        return redirect('dashboard')
    
    # Vérifier si le responsable est associé à une équipe
    try:
        responsable = hasattr(request.user, 'responsable_profile') and request.user.responsable_profile
        equipe_responsable = responsable.equipe_geree if responsable else None
        
        if not equipe_responsable:
            messages.error(request, "Vous devez être responsable d'une équipe pour créer des matchs.")
            return redirect('dashboard')
            
    except Exception as e:
        messages.error(request, f"Erreur lors de la vérification de votre équipe: {str(e)}")
        return redirect('dashboard')
    
    if request.method == 'POST':
        equipe_a_id = request.POST.get('equipe_a')
        equipe_b_id = request.POST.get('equipe_b')
        date = request.POST.get('date')
        lieu = request.POST.get('lieu', '')
        
        errors = []
        if not equipe_a_id:
            errors.append("Veuillez sélectionner l'équipe A.")
        if not equipe_b_id:
            errors.append("Veuillez sélectionner l'équipe B.")
        if equipe_a_id and equipe_b_id and equipe_a_id == equipe_b_id:
            errors.append("Les deux équipes ne peuvent pas être identiques.")
        if not date:
            errors.append("Veuillez spécifier une date pour le match.")
        
        # Vérifier que l'équipe du responsable est bien incluse
        if str(equipe_responsable.id) != equipe_a_id and str(equipe_responsable.id) != equipe_b_id:
            errors.append("Vous ne pouvez créer des matchs que pour votre propre équipe.")
        
        if not errors:
            try:
                from equipes.models import Equipe
                equipe_a = Equipe.objects.get(id=equipe_a_id)
                equipe_b = Equipe.objects.get(id=equipe_b_id)
                
                # Utiliser les noms de champs corrects du modèle Match
                from matchs.models import Match
                match = Match(
                    equipe_a=equipe_a,
                    equipe_b=equipe_b,
                    date=date,
                    lieu=lieu,
                    tournoi=None  # Match amical sans tournoi
                )
                match.save()
                
                messages.success(request, f"Le match {equipe_a.nom} vs {equipe_b.nom} a été créé avec succès.")
                return redirect('matchs:detail', pk=match.id)
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite: {str(e)}")
        else:
            for error in errors:
                messages.error(request, error)
    
    # Récupérer la liste des équipes pour le formulaire (toutes sauf la propre équipe du responsable)
    from equipes.models import Equipe
    equipes_adverses = Equipe.objects.exclude(id=equipe_responsable.id).order_by('nom')
    
    context = {
        'equipe_responsable': equipe_responsable,
        'equipes_adverses': equipes_adverses,
        'now': timezone.now().strftime('%Y-%m-%dT%H:%M')
    }
    
    return render(request, 'matchs/creer_match.html', context)

@login_required
def modifier_match(request, pk):
    """
    Vue pour modifier un match existant.
    """
    match = get_object_or_404(Match, pk=pk)
    
    # Vérifier que l'utilisateur est autorisé (responsable de l'une des équipes ou admin)
    # Vérifier si le responsable est associé à une équipe
    try:
        responsable = hasattr(request.user, 'responsable_profile') and request.user.responsable_profile
        equipe_responsable = responsable.equipe_geree if responsable else None
        
        is_responsable_a = equipe_responsable and equipe_responsable == match.equipe_a
        is_responsable_b = equipe_responsable and equipe_responsable == match.equipe_b
        
        if not (is_responsable_a or is_responsable_b or request.user.is_staff):
            messages.error(request, "Vous n'êtes pas autorisé à modifier ce match.")
            return redirect('matchs:detail', pk=pk)
    except Exception as e:
        messages.error(request, f"Erreur lors de la vérification des permissions: {str(e)}")
        return redirect('matchs:detail', pk=pk)
    
    if request.method == 'POST':
        equipe_a_id = request.POST.get('equipe_a')
        equipe_b_id = request.POST.get('equipe_b')
        date = request.POST.get('date')
        lieu = request.POST.get('lieu', '')
        
        errors = []
        if not equipe_a_id:
            errors.append("Veuillez sélectionner l'équipe A.")
        if not equipe_b_id:
            errors.append("Veuillez sélectionner l'équipe B.")
        if equipe_a_id and equipe_b_id and equipe_a_id == equipe_b_id:
            errors.append("Les deux équipes ne peuvent pas être identiques.")
        if not date:
            errors.append("Veuillez spécifier une date pour le match.")
        
        if not errors:
            try:
                equipe_a = Equipe.objects.get(id=equipe_a_id)
                equipe_b = Equipe.objects.get(id=equipe_b_id)
                
                match.equipe_a = equipe_a
                match.equipe_b = equipe_b
                match.date = date
                match.lieu = lieu
                match.save()
                
                messages.success(request, f"Le match {equipe_a.nom} vs {equipe_b.nom} a été modifié avec succès.")
                return redirect('matchs:detail', pk=pk)
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite: {str(e)}")
        else:
            for error in errors:
                messages.error(request, error)
    
    # Récupérer la liste des équipes pour le formulaire
    equipes = Equipe.objects.all().order_by('nom')
    context = {
        'match': match,
        'equipes': equipes,
        'date_match': match.date.strftime('%Y-%m-%dT%H:%M')
    }
    
    return render(request, 'matchs/modifier_match.html', context)

@login_required
def enregistrer_resultat(request, pk):
    """
    Vue pour enregistrer le résultat d'un match.
    """
    match = get_object_or_404(Match, pk=pk)
    
    # Vérifier que l'utilisateur est autorisé (responsable de l'une des équipes ou admin)
    try:
        responsable = hasattr(request.user, 'responsable_profile') and request.user.responsable_profile
        equipe_responsable = responsable.equipe_geree if responsable else None
        
        is_responsable_a = equipe_responsable and equipe_responsable == match.equipe_a
        is_responsable_b = equipe_responsable and equipe_responsable == match.equipe_b
        
        if not (is_responsable_a or is_responsable_b or request.user.is_staff):
            messages.error(request, "Vous n'êtes pas autorisé à enregistrer ce résultat.")
            return redirect('matchs:detail', pk=pk)
    except Exception as e:
        messages.error(request, f"Erreur lors de la vérification des permissions: {str(e)}")
        return redirect('matchs:detail', pk=pk)
    
    if request.method == 'POST':
        score_a = request.POST.get('score_a')
        score_b = request.POST.get('score_b')
        
        errors = []
        try:
            score_a = int(score_a)
            score_b = int(score_b)
            
            if score_a < 0 or score_b < 0:
                errors.append("Les scores doivent être des nombres positifs.")
        except (ValueError, TypeError):
            errors.append("Les scores doivent être des nombres entiers.")
        
        if not errors:
            match.score_equipe_a = score_a
            match.score_equipe_b = score_b
            match.termine = True
            match.save()
            
            messages.success(request, f"Résultat enregistré: {match.equipe_a.nom} {score_a} - {score_b} {match.equipe_b.nom}")
            return redirect('matchs:detail', pk=pk)
        else:
            for error in errors:
                messages.error(request, error)
    
    return render(request, 'matchs/enregistrer_resultat.html', {'match': match})

@login_required
def supprimer_match(request, pk):
    """
    Vue pour supprimer un match.
    """
    match = get_object_or_404(Match, pk=pk)
    
    # Vérifier que l'utilisateur est autorisé (responsable de l'une des équipes ou admin)
    try:
        responsable = hasattr(request.user, 'responsable_profile') and request.user.responsable_profile
        equipe_responsable = responsable.equipe_geree if responsable else None
        
        is_responsable_a = equipe_responsable and equipe_responsable == match.equipe_a
        is_responsable_b = equipe_responsable and equipe_responsable == match.equipe_b
        
        if not (is_responsable_a or is_responsable_b or request.user.is_staff):
            messages.error(request, "Vous n'êtes pas autorisé à supprimer ce match.")
            return redirect('matchs:detail', pk=pk)
    except Exception as e:
        messages.error(request, f"Erreur lors de la vérification des permissions: {str(e)}")
        return redirect('matchs:detail', pk=pk)
    
    if request.method == 'POST':
        match.delete()
        messages.success(request, "Le match a été supprimé avec succès.")
        return redirect('matchs:liste')
    
    return render(request, 'matchs/supprimer_match.html', {'match': match})

def liste_tournois(request):
    """
    Fonction pour rediriger vers la liste des tournois.
    Cette fonction est ajoutée pour être compatible avec votre urls.py existant.
    """
    from django.shortcuts import redirect
    return redirect('tournois:liste')
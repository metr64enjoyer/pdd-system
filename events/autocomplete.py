from dal import autocomplete
from .models import Organization


class OrganizationAutocomplete(autocomplete.Select2QuerySetView):
    """Автодополнение для поиска организаций"""
    
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Organization.objects.none()
        
        qs = Organization.objects.filter(is_active=True)
        
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        
        return qs[:20]
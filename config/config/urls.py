from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from gestionBatiment.views import ClientViewSet, BatimentViewSet, NiveauViewSet,  TypeBureauViewSet, BureauViewSet, ContratViewSet, LocationViewSet, PaiementViewSet, ReservationViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView 


router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'batiments', BatimentViewSet, basename='batiment')
router.register(r'types-bureau', TypeBureauViewSet, basename='typebureau')  
router.register(r'niveaux', NiveauViewSet, basename='niveau')
router.register(r'bureaux', BureauViewSet, basename='bureau')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'contrats', ContratViewSet, basename='contrat')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'paiements', PaiementViewSet, basename='paiement')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
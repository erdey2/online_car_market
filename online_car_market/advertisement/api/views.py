from .serializers import AdvertisementSerializer
from ..models import Advertisement
from rest_framework import viewsets

class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all()
    serializer_class = AdvertisementSerializer

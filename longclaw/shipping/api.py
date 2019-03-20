from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from longclaw.shipping import models, utils, serializers
from longclaw.configuration.models import Configuration

from .signals import address_modified

class AddressViewSet(viewsets.ModelViewSet):
    """
    Create, list and view Addresses
    """
    queryset = models.Address.objects.all()
    serializer_class = serializers.AddressSerializer
    
    def perform_create(self, serializer):
        output = super().perform_create(serializer)
        instance = serializer.instance
        address_modified.send(sender=models.Address, instance=instance)
    
    def perform_update(self, serializer):
        output = super().perform_update(serializer)
        instance = serializer.instance
        address_modified.send(sender=models.Address, instance=instance)
    
    def perform_destroy(self, instance):
        output = super().perform_destroy(instance)
        address_modified.send(sender=models.Address, instance=instance)


@api_view(['GET'])
@permission_classes({permissions.AllowAny})
def shipping_cost(request):
    """ Returns the shipping cost for a given country
    If the shipping cost for the given country has not been set, it will
    fallback to the default shipping cost if it has been enabled in the app
    settings
    """
    try:
        code = request.query_params.get('country_code')
    except AttributeError:
        return Response(data={"message": "No country code supplied"},
                        status=status.HTTP_400_BAD_REQUEST)

    option = request.query_params.get('shipping_rate_name', 'standard')
    try:
        settings = Configuration.for_site(request.site)
        data = utils.get_shipping_cost(settings, code, option)
        response = Response(data=data, status=status.HTTP_200_OK)
    except utils.InvalidShippingRate:
        response = Response(data={"message": "Shipping option {} is invalid".format(option)},
                            status=status.HTTP_400_BAD_REQUEST)
    except utils.InvalidShippingCountry:
        response = Response(data={"message": "Shipping to {} is not available".format(code)},
                            status=status.HTTP_400_BAD_REQUEST)

    return response


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def shipping_countries(request):
    """ Get all shipping countries
    """
    queryset = models.Country.objects.exclude(shippingrate=None)
    serializer = serializers.CountrySerializer(queryset, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def shipping_options(request, country):
    """
    Get the shipping options for a given country
    """
    qrs = models.ShippingRate.objects.filter(countries__in=[country])
    serializer = serializers.ShippingRateSerializer(qrs, many=True)
    return Response(
        data=serializer.data,
        status=status.HTTP_200_OK
    )

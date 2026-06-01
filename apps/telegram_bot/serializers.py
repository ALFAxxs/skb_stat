from rest_framework import serializers
from apps.laboratory.models import LabResult, LabResultValue, LabParameter
from apps.services.models import Service, ServiceCategory
from .models import TelegramUser, PatientTelegramBinding, ResultNotification


class LabResultListSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name')
    category      = serializers.CharField(source='template.category')
    category_display = serializers.CharField(source='template.get_category_display')
    created_date  = serializers.SerializerMethodField()
    created_time  = serializers.SerializerMethodField()

    class Meta:
        model  = LabResult
        fields = ['id', 'template_name', 'category', 'category_display',
                  'status', 'created_date', 'created_time', 'created_at']

    def get_created_date(self, obj):
        return obj.created_at.strftime('%d.%m.%Y')

    def get_created_time(self, obj):
        return obj.created_at.strftime('%H:%M')


class LabParamValueSerializer(serializers.Serializer):
    name         = serializers.CharField(source='parameter.name')
    name_ru      = serializers.CharField(source='parameter.name_ru')
    unit         = serializers.CharField(source='parameter.unit')
    value        = serializers.CharField()
    value_status = serializers.CharField()
    normal_range = serializers.SerializerMethodField()

    def get_normal_range(self, obj):
        gender = self.context.get('gender', 'M')
        return obj.parameter.get_normal_display(gender)


class LabResultDetailSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name')
    category      = serializers.CharField(source='template.get_category_display')
    created_at    = serializers.SerializerMethodField()
    verified_by   = serializers.SerializerMethodField()
    created_by    = serializers.SerializerMethodField()
    groups        = serializers.SerializerMethodField()
    has_pdf       = serializers.SerializerMethodField()

    class Meta:
        model  = LabResult
        fields = ['id', 'template_name', 'category', 'status', 'conclusion',
                  'created_at', 'created_by', 'verified_by', 'groups', 'has_pdf']

    def get_created_at(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')

    def get_verified_by(self, obj):
        if obj.verified_by:
            return obj.verified_by.get_full_name() or obj.verified_by.username
        return None

    def get_created_by(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_has_pdf(self, obj):
        return hasattr(obj, 'pdf_file') and not obj.pdf_file.is_expired

    def get_groups(self, obj):
        gender = self.context.get('gender', 'M')
        values = {v.parameter_id: v for v in obj.values.select_related('parameter__group')}
        params = obj.template.parameters.select_related('group').order_by('sort_order', 'name')

        groups = {}
        ungrouped = []
        for p in params:
            rv = values.get(p.pk)
            if not rv:
                continue
            entry = {
                'name':         p.name,
                'name_ru':      p.name_ru,
                'unit':         p.unit,
                'value':        rv.value,
                'value_status': rv.value_status,
                'normal_range': p.get_normal_display(gender),
            }
            if p.group_id:
                gname = p.group.name
                if gname not in groups:
                    groups[gname] = []
                groups[gname].append(entry)
            else:
                ungrouped.append(entry)

        result = [{'group': g, 'params': params_list}
                  for g, params_list in groups.items()]
        if ungrouped:
            result.append({'group': None, 'params': ungrouped})
        return result


class ServicePriceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name')
    price         = serializers.SerializerMethodField()

    class Meta:
        model  = Service
        fields = ['id', 'name', 'category_name', 'price']

    def get_price(self, obj):
        return float(obj.price_normal or 0)
# serializers/serializers.py

from rest_framework import serializers
from apps.products.models import Product, ProductImage, ProductFeature, ProductSpecification, ProductVariant, Brand, Category
from django.db import transaction


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            'id', 
            'image', 
            'order'
        ]

class ProductFeatureSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = ProductFeature
        fields = ['feature', 'id', 'product']

class ProductSpecificationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = ProductSpecification
        fields = [
            'id',	
            'name',	
            'value',
            'product'
        ]

class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    features = ProductFeatureSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'brand',
            'description',
            'category',
            'sku',
            'price',
            'original_price',
            'discount',
            'seller',
            'stock',
            'images',
            'features',
            'specifications',
        ]

class ProductCheckoutSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'brand',
            'category',
            'sku',
            'price',
            'original_price',
            'discount',
            'images',
        ]


class ProductCreateSerializer(serializers.ModelSerializer):
    seller = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    features = ProductFeatureSerializer(many=True, required=False)
    specifications = ProductSpecificationSerializer(many=True, required=False)
    images = ProductImageSerializer(many=True, read_only=True)
    
    # Campos para escribir los IDs de relaciones
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source='brand',
        required=False,
        write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        required=False,
        write_only=True
    )
    
    # Campos para mostrar datos completos en la respuesta
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'brand',
            'description', 
            'category', 
            'sku', 
            'price', 
            'original_price', 
            'discount', 
            'seller', 
            'stock', 
            'features', 
            'specifications',
            'images',
            'brand_id',
            'category_id',
            'paused',
            'paused_date'
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        features_data = validated_data.pop('features', [])
        specifications_data = validated_data.pop('specifications', [])

        product = Product.objects.create(**validated_data)

        for feature_data in features_data:
            feature_data.pop('product', None)
            ProductFeature.objects.create(product=product, **feature_data)

        for specification_data in specifications_data:
            specification_data.pop('product', None)
            ProductSpecification.objects.create(product=product, **specification_data)

        return product

class ProductUpdateSerializer(serializers.ModelSerializer):
    seller = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    features = ProductFeatureSerializer(many=True, required=False)
    specifications = ProductSpecificationSerializer(many=True, required=False)
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    # Adding write-only fields for brand_id and category_id
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source='brand',
        required=False,
        write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        required=False,
        write_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'brand', 
            'brand_id',
            'description', 
            'category',
            'category_id', 
            'sku', 
            'price', 
            'original_price', 
            'discount', 
            'seller', 
            'stock', 
            'features', 
            'specifications',
            'images',
            'paused',
            'paused_date'
        ]
    
    @transaction.atomic
    def update(self, instance, validated_data):
        features_data = validated_data.pop('features', [])
        specifications_data = validated_data.pop('specifications', [])

        # Actualizar los campos básicos del producto
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualizar features
        if features_data:
            existing_features = {str(feature.id): feature for feature in instance.features.all()}
            
            # Crear/actualizar features
            for feature_data in features_data:
                feature_id = feature_data.get('id')
                # Remove product if it exists in the data
                feature_data.pop('product', None)
                
                if feature_id and str(feature_id) in existing_features:
                    # Actualizar característica existente
                    feature = existing_features.pop(str(feature_id))
                    for attr, value in feature_data.items():
                        if attr != 'id':
                            setattr(feature, attr, value)
                    feature.save()
                else:
                    # Crear nueva característica (con o sin id)
                    # Si tiene id pero no existe, o si no tiene id, se crea una nueva
                    cleaned_data = {k: v for k, v in feature_data.items() if k != 'id'}
                    ProductFeature.objects.create(product=instance, **cleaned_data)

        # Actualizar specifications
        if specifications_data:
            existing_specs = {str(spec.id): spec for spec in instance.specifications.all()}
            
            # Crear/actualizar specifications
            for spec_data in specifications_data:
                spec_id = spec_data.get('id')
                # Remove product if it exists in the data
                spec_data.pop('product', None)
                
                if spec_id and str(spec_id) in existing_specs:
                    # Actualizar especificación existente
                    spec = existing_specs.pop(str(spec_id))
                    for attr, value in spec_data.items():
                        if attr != 'id':
                            setattr(spec, attr, value)
                    spec.save()
                else:
                    # Crear nueva especificación (con o sin id)
                    # Si tiene id pero no existe, o si no tiene id, se crea una nueva
                    cleaned_data = {k: v for k, v in spec_data.items() if k != 'id'}
                    ProductSpecification.objects.create(product=instance, **cleaned_data)

        return instance

class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    features = ProductFeatureSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'brand',
            'description',
            'category',
            'sku',
            'price',
            'original_price',
            'discount',
            'seller',
            'stock',
            'images',
            'features',
            'specifications',
            'brand',
            'paused',
            'paused_date'
        ]

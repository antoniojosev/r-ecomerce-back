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
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = [
            'id', 
            'image', 
            'order'
        ]
    
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            url = obj.image.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None

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
    """
    Serializer para el modelo Product con manejo de marcas, categorías e imágenes.
    Permite crear marcas y categorías por nombre si no existen.
    Permite cargar imágenes usando el campo 'uploaded_images'.
    """
    seller = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    # El campo images se usará solo para la respuesta
    images = ProductImageSerializer(many=True, required=False, read_only=True)
    # Para las imágenes que se envían en la solicitud
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    brand = serializers.CharField(required=False)
    category = serializers.CharField(required=False)

    class Meta:
        model = Product
        fields = ['id', 'name', 'brand', 'description', 'category', 'sku', 'price', 'original_price', 
                  'discount', 'seller', 'stock', 'paused', 'paused_date', 'images', 'variants', 'uploaded_images']

    def create(self, validated_data):
        print("=== INICIO CREACION DE PRODUCTO CON IMAGENES ===")
        print(f"Datos recibidos (claves): {list(validated_data.keys())}")
        
        # 1. Extraer las imágenes y variantes
        uploaded_images = validated_data.pop('uploaded_images', [])
        variants_data = validated_data.pop('variants', [])
        
        print(f"Tenemos {len(uploaded_images)} imágenes para cargar")
        
        # 2. Procesar brand por nombre si es necesario
        brand_data = validated_data.pop('brand', None)
        if brand_data and isinstance(brand_data, str):
            print(f"Creando/obteniendo marca: {brand_data}")
            brand, created = Brand.objects.get_or_create(name=brand_data)
            validated_data['brand'] = brand
            if created:
                print(f"Marca {brand_data} creada correctamente")
        
        # 3. Procesar category por nombre si es necesario
        category_data = validated_data.pop('category', None)
        if category_data and isinstance(category_data, str):
            print(f"Creando/obteniendo categoría: {category_data}")
            category, created = Category.objects.get_or_create(name=category_data)
            validated_data['category'] = category
            if created:
                print(f"Categoría {category_data} creada correctamente")
        
        # 4. Crear el producto
        try:
            product = Product.objects.create(**validated_data)
            print(f"Producto creado con ID: {product.id}")
        except Exception as e:
            print(f"Error al crear producto: {str(e)}")
            raise
        
        # 5. Crear las imágenes relacionadas
        for i, image_file in enumerate(uploaded_images):
            try:
                print(f"Intentando guardar imagen {i+1}: {getattr(image_file, 'name', 'Sin nombre')}")
                image = ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    order=i
                )
                print(f"¡Imagen guardada correctamente con ID {image.id}!")
            except Exception as e:
                print(f"ERROR AL GUARDAR IMAGEN: {str(e)}")
                # Continuar con las siguientes imágenes a pesar del error
        
        # Crear las variantes relacionadas
        for variant_data in variants_data:
            ProductVariant.objects.create(product=product, **variant_data)

        return product

    def update(self, instance, validated_data):
        # Depuración completa para update
        print("==================== INICIO DEBUG UPDATE ====================")
        print("Tipo de validated_data:", type(validated_data))
        print("Claves en validated_data:", list(validated_data.keys()))
        print("UPDATE METHOD SE ESTA EJECUTANDO")
        
        # Extraer las imágenes subidas y variantes del producto
        uploaded_images = validated_data.pop('uploaded_images', [])
        print(f"Tipo de uploaded_images en UPDATE: {type(uploaded_images)} - Contenido: {uploaded_images}")
        variants_data = validated_data.pop('variants', [])
        
        # Procesar brand si se proporciona como texto
        brand_data = validated_data.pop('brand', None)
        if brand_data and isinstance(brand_data, str):
            brand, created = Brand.objects.get_or_create(name=brand_data)
            instance.brand = brand
            
        # Procesar category si se proporciona como texto
        category_data = validated_data.pop('category', None)
        if category_data and isinstance(category_data, str):
            category, created = Category.objects.get_or_create(name=category_data)
            instance.category = category
        
        # Actualizar los campos del producto
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualizar las imágenes relacionadas
        # Si hay imágenes subidas, crear nuevas entradas
        for i, image_file in enumerate(uploaded_images):
            try:
                img = ProductImage.objects.create(
                    product=instance, 
                    image=image_file,
                    order=i + ProductImage.objects.filter(product=instance).count()  # Agregar al final
                )
                print("DEBUG - Imagen actualizada con ID:", img.id)
            except Exception as e:
                print("DEBUG - Error al actualizar imagen:", str(e))
        
        # Actualizar las variantes relacionadas
        for variant_data in variants_data:
            variant_id = variant_data.get('id')
            if variant_id:
                variant = ProductVariant.objects.get(id=variant_id)
                variant.name = variant_data.get('name', variant.name)
                variant.value = variant_data.get('value', variant.value)
                variant.stock = variant_data.get('stock', variant.stock)
                variant.price = variant_data.get('price', variant.price)
                variant.save()
            else:
                ProductVariant.objects.create(product=instance, **variant_data)

        return instance



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

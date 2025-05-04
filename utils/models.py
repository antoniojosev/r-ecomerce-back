import uuid
from typing import ClassVar

from django.db import models, transaction
from django.db.models.options import Options
from django.utils.timezone import now


class SoftDeleteManager(models.Manager):  # noqa: R0903
    """Manager to retrieve only non-deleted objects."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):  # noqa: R0903
    """Base model with Soft Delete support and cascade restoration."""

    _meta: ClassVar[Options]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()  # Only shows active objects
    all_objects = models.Manager()  # Shows all objects, including deleted ones

    @property
    def is_deleted(self):
        """Determines if the instance is considered deleted."""
        return self.deleted_at is not None

    @transaction.atomic
    def delete(self, using=None, keep_parents=False, _deletion_context=None):  # noqa: A003
        """Marks the object as deleted and handles relationships accordingly."""
        if self.is_deleted:
            return

        # Initialize deletion context to track objects being deleted
        if _deletion_context is None:
            _deletion_context = set()

        # If this object is already in the deletion context, skip to avoid cycles
        obj_key = (self.__class__, self.pk)
        if obj_key in _deletion_context:
            return

        # Add this object to the deletion context
        _deletion_context.add(obj_key)

        self.deleted_at = now()
        self.save()

        # Solo necesitamos manejar las FKs para SET_NULL
        self.handle_foreign_keys()

        # Sigue manejando muchos a muchos normalmente
        self.handle_many_to_many()

        # Esta es la que realmente debe manejar la cascada hacia abajo
        self.handle_cascade_delete(_deletion_context)

    def restore(self):
        """Restores the deleted object and cascades restoration."""
        if not self.is_deleted:
            return  # Avoid redundant restorations

        self.deleted_at = None
        self.save()

        self.handle_cascade_restore()

    def handle_foreign_keys(self):
        """Manages only SET_NULL behavior for foreign keys we own."""
        changed = False
        for field in self._meta.fields:
            if isinstance(field, (models.OneToOneField, models.ForeignKey)):
                # Solo nos interesa configurar campos a NULL si es requerido
                if hasattr(field, "remote_field") and hasattr(field.remote_field, "on_delete"):
                    if field.remote_field.on_delete is models.SET_NULL and field.null:
                        setattr(self, field.name, None)
                        changed = True
                    # No procesamos CASCADE aquí - eso iría hacia arriba

        if changed:
            self.save()

    def handle_many_to_many(self):
        """Removes ManyToMany relationships without deleting related objects."""
        for field in self._meta.many_to_many:
            getattr(self, field.name).clear()

    def handle_cascade_delete(self, _deletion_context=None):
        """Finds dependent objects and deletes them in cascade."""
        if _deletion_context is None:
            _deletion_context = set()

        for relation in self._meta.related_objects:
            # Solo nos interesan las relaciones con on_delete definido
            if not hasattr(relation, "on_delete"):
                # Si el campo es NULL, actualizamos la referencia
                if relation.field.null:
                    related_name = relation.related_name or relation.name + "_set"
                    try:
                        related_objects = getattr(self, related_name).all()
                        for obj in related_objects:
                            setattr(obj, relation.field.name, None)
                            obj.save()
                    except AttributeError:
                        # En caso de que la relación no tenga el atributo o manager esperado
                        pass
                continue

            # Esta es la cascada correcta: objetos que tienen FK hacia este objeto
            if relation.on_delete is models.CASCADE:
                related_name = relation.related_name or relation.name + "_set"
                try:
                    related_objects = getattr(self, related_name).all()
                    for obj in related_objects:
                        obj.delete(_deletion_context=_deletion_context)
                except AttributeError:
                    # Por si no existe el atributo o manager
                    pass

    def handle_cascade_restore(self):
        """Restores in cascade the objects that depend on this one."""
        for relation in self._meta.related_objects:
            if not hasattr(relation, "on_delete"):
                continue

            if relation.on_delete is models.CASCADE:
                related_model = relation.related_model
                related_objects = related_model.all_objects.filter(
                    **{relation.field.name: self}, deleted_at__isnull=False
                ).iterator()
                for obj in related_objects:
                    obj.restore()

    class Meta:  # noqa: R0903
        abstract = True

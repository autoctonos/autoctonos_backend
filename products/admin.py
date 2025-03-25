from django.contrib import admin
from .models import Post

@admin.action(description="Aprobar posts seleccionados")
def aprobar_posts(modeladmin, request, queryset):
    queryset.update(estado='Aprobado', mensaje=None)

@admin.action(description="Rechazar posts seleccionados")
def rechazar_posts(modeladmin, request, queryset):
    for post in queryset:
        post.estado = 'Rechazado'
        post.mensaje = "Rechazado por el administrador" 
        post.save()

class PostAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'id_usuario', 'estado', 'created_at')
    list_filter = ('estado', 'created_at')
    search_fields = ('nombre', 'descripcion')
    actions = [aprobar_posts, rechazar_posts]

admin.site.register(Post, PostAdmin)


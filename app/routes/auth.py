# app/routes/auth.py
# ============================================================
# RUTAS DE AUTENTICACIÓN: registro, login, logout
# ============================================================

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.extensions import get_supabase
from app.auth_utils import hash_password, verify_password

auth_bp = Blueprint('auth', __name__)

# ── REGISTRO ─────────────────────────────────────────────────
@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Muestra el form de registro (GET) y procesa el registro (POST)."""

    if request.method == 'POST':
        # 1. Recoger datos del formulario
        nombre    = request.form.get('nombre', '').strip()
        apellido  = request.form.get('apellido', '').strip()
        email     = request.form.get('email', '').strip().lower()
        codigo    = request.form.get('codigo', '').strip()
        programa  = request.form.get('programa', '').strip()
        password  = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        # 2. Validaciones básicas
        errores = []
        if not all([nombre, apellido, email, password]):
            errores.append('Todos los campos obligatorios deben estar completos.')
        if password != password2:
            errores.append('Las contraseñas no coinciden.')
        if len(password) < 6:
            errores.append('La contraseña debe tener al menos 6 caracteres.')
        if '@' not in email:
            errores.append('El correo electrónico no es válido.')

        if errores:
            for error in errores:
                flash(error, 'danger')
            return render_template('auth/registro.html')

        try:
            sb = get_supabase()

            # 3. Verificar si el email ya existe
            existe = sb.table('usuarios').select('id').eq('email', email).execute()
            if existe.data:
                flash('Ya existe una cuenta con ese correo electrónico.', 'danger')
                return render_template('auth/registro.html')

            # 4. Encriptar contraseña e insertar usuario
            nuevo_usuario = {
                'nombre':        nombre,
                'apellido':      apellido,
                'email':         email,
                'codigo':        codigo or None,
                'programa':      programa or None,
                'password_hash': hash_password(password),
                'rol':           'estudiante'
            }

            resultado = sb.table('usuarios').insert(nuevo_usuario).execute()

            if resultado.data:
                flash('¡Cuenta creada exitosamente! Ya puedes iniciar sesión.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Error al crear la cuenta. Intenta de nuevo.', 'danger')

        except Exception as e:
            flash(f'Error del servidor: {str(e)}', 'danger')

    return render_template('auth/registro.html')


# ── LOGIN ─────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # ── CORRECCIÓN: verificar sesión sin redirigir a /
    if 'usuario_id' in session:
        return redirect(url_for('vacantes.index'))  # ← directo a vacantes

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Ingresa tu correo y contraseña.', 'danger')
            return redirect(url_for('vacantes.index'))  # ← no a home()


        return render_template('auth/login.html')
            

        try:
            sb = get_supabase()

            # Buscar usuario por email
            resultado = (
                sb.table('usuarios')
                .select('*')
                .eq('email', email)
                .eq('activo', True)
                .execute()
            )

            if not resultado.data:
                flash('Correo o contraseña incorrectos.', 'danger')
                return render_template('auth/login.html')

            usuario = resultado.data[0]

            # Verificar contraseña
            if not verify_password(password, usuario.get('password_hash', '')):
                flash('Correo o contraseña incorrectos.', 'danger')
                return render_template('auth/login.html')

            # ✅ Login exitoso — guardar en sesión
            session.permanent = True
            session['usuario_id'] = usuario['id']
            session['nombre']     = usuario['nombre']
            session['apellido']   = usuario['apellido']
            session['email']      = usuario['email']
            session['rol']        = usuario['rol']
            session['programa']   = usuario.get('programa', '')

            flash(f'¡Bienvenido, {usuario["nombre"]}!', 'success')
            return redirect(url_for('vacantes.index'))

        except Exception as e:
            flash(f'Error del servidor: {str(e)}', 'danger')

    return render_template('auth/login.html')


# ── LOGOUT ────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    """Cierra la sesión y redirige al login."""
    nombre = session.get('nombre', 'Usuario')
    session.clear()
    flash(f'Hasta luego, {nombre}. ¡Sesión cerrada correctamente!', 'info')
    return redirect(url_for('auth.login'))


# ── PERFIL ────────────────────────────────────────────────────
@auth_bp.route('/perfil')
def perfil():
    """Muestra el perfil del usuario logueado."""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('auth/perfil.html')
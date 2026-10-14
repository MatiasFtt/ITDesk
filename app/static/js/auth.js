
const loginForm = document.querySelector("#login-form");
const registroForm = document.querySelector("#registro-form");

function mostrarMensaje(texto, tipo = "error") {
    const elemento = document.querySelector("#form-message");
    if (!elemento) return;

    elemento.textContent = texto;
    elemento.className = `message ${tipo}`;
    elemento.hidden = false;
}

function obtenerDetalleError(datos) {
    if (typeof datos.detail === "string") {
        return datos.detail;
    }

    if (Array.isArray(datos.detail)) {
        return datos.detail
            .map((error) => error.msg)
            .join(". ");
    }

    return "No se pudo completar la solicitud.";
}

async function enviarFormulario(url, datos, boton) {
    boton.disabled = true;
    boton.textContent = "Procesando...";

    try {
        const respuesta = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(datos)
        });

        const resultado = await respuesta.json();

        if (!respuesta.ok) {
            mostrarMensaje(obtenerDetalleError(resultado));
            return null;
        }

        return resultado;
    } catch {
        mostrarMensaje(
            "No se pudo conectar con el servidor. Verificá que ITDesk esté funcionando."
        );
        return null;
    } finally {
        boton.disabled = false;
        boton.innerHTML = 'Continuar <span aria-hidden="true">→</span>';
    }
}

if (loginForm) {
    loginForm.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const boton = loginForm.querySelector("button[type='submit']");
        const datos = {
            email: loginForm.email.value.trim(),
            password: loginForm.password.value
        };

        const resultado = await enviarFormulario(
            "/api/auth/login",
            datos,
            boton
        );

        if (resultado?.access_token) {
            // Para esta versión local de desarrollo.
            sessionStorage.setItem("itdesk_token", resultado.access_token);
            window.location.assign("/dashboard");
        }
    });
}

if (registroForm) {
    registroForm.addEventListener("submit", async (evento) => {
        evento.preventDefault();

        const boton = registroForm.querySelector("button[type='submit']");
        const password = registroForm.password.value;
        const confirmacion = registroForm.elements["confirm-password"].value;

        if (password !== confirmacion) {
            mostrarMensaje("Las contraseñas no coinciden.");
            return;
        }

        const resultado = await enviarFormulario(
            "/api/auth/registro",
            {
                nombre: registroForm.nombre.value.trim(),
                email: registroForm.email.value.trim(),
                password
            },
            boton
        );

        if (resultado) {
            mostrarMensaje(
                "Cuenta creada correctamente. Ahora podés iniciar sesión.",
                "success"
            );

            registroForm.reset();

            window.setTimeout(() => {
                window.location.assign("/login");
            }, 1200);
        }
    });
}

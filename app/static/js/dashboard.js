const token = sessionStorage.getItem("itdesk_token");
const message = document.querySelector("#dashboard-message");
const ticketList = document.querySelector("#ticket-list");
const ticketForm = document.querySelector("#ticket-form");
const ticketDetail = document.querySelector("#ticket-detail");
let currentUserRole = "USUARIO";
let ticketsActuales = [];
const ticketsEnActualizacion = new Set();
const estadosTicket = [
    { id: "ABIERTO", label: "Recibido", color: "#94a3b8" },
    { id: "EN_PROCESO", label: "En proceso", color: "#3b82f6" },
    { id: "SOLUCIONANDO", label: "Estamos solucionando", color: "#8b5cf6" },
    { id: "ESPERANDO_USUARIO", label: "Esperando respuesta", color: "#f59e0b" },
    { id: "RESUELTO", label: "Finalizado", color: "#22a06b" },
    { id: "CERRADO", label: "Cerrado", color: "#475569" }
];

function etiquetaEstado(id) {
    return estadosTicket.find((estado) => estado.id === id)?.label || id.replaceAll("_", " ");
}

function notify(text, kind = "error") {
    message.textContent = text;
    message.className = `message ${kind}`;
    message.hidden = false;
}

async function api(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: { Authorization: `Bearer ${token}`, ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers }
    });
    if (response.status === 401) {
        sessionStorage.removeItem("itdesk_token");
        window.location.replace("/login");
        throw new Error("Tu sesión venció. Inicia sesión nuevamente.");
    }
    const responseText = response.status === 204 ? "" : await response.text();
    let body = null;
    if (responseText) {
        try { body = JSON.parse(responseText); }
        catch { body = { detail: responseText.trim() || `Error del servidor (${response.status}).` }; }
    }
    if (!response.ok) {
        const detail = typeof body?.detail === "string" ? body.detail : `Error del servidor (${response.status}).`;
        throw new Error(detail.includes("Internal Server Error")
            ? "El servidor falló al procesar el ticket. Revisa los registros de la aplicación e inténtalo de nuevo."
            : detail);
    }
    return body;
}

async function cargarUsuario() {
    if (!token) return window.location.replace("/login");
    try {
        const usuario = await api("/api/auth/me");
        currentUserRole = usuario.rol;
        if (currentUserRole === "ADMIN") {
            document.querySelector("#admin-overview").hidden = false;
            document.querySelector("#tickets-heading").textContent = "Tickets del área";
            document.querySelector("#new-ticket-button").hidden = true;
            ticketForm.hidden = true;
        }
        document.querySelector("#user-name").textContent = usuario.nombre;
        document.querySelector("#user-email").textContent = usuario.email;
        document.querySelector("#user-role").textContent = usuario.rol;
        document.querySelector("#user-avatar").textContent = usuario.nombre.trim().charAt(0).toUpperCase();
        await Promise.all([cargarDepartamentos(), cargarTickets()]);
    } catch (error) { notify(error.message); }
}

async function cargarDepartamentos() {
    const departamentos = await api("/api/departamentos/");
    const selector = document.querySelector("#ticket-department");
    selector.replaceChildren(...departamentos.map((d) => {
        const option = document.createElement("option");
        option.value = d.id;
        option.textContent = d.nombre;
        return option;
    }));
    if (!departamentos.length) document.querySelector("#new-ticket-button").disabled = true;
}

async function cargarTickets() {
    let tickets;
    try { tickets = await api("/api/tickets/"); }
    catch (error) {
        ticketList.replaceChildren();
        const failure = document.createElement("p");
        failure.className = "empty-state";
        failure.textContent = `No se pudieron cargar los tickets: ${error.message}`;
        ticketList.append(failure);
        throw error;
    }
    ticketsActuales = tickets;
    dibujarTickets();
}

function dibujarTickets() {
    ticketList.replaceChildren();
    if (currentUserRole === "ADMIN") actualizarGrafico(ticketsActuales);
    if (!ticketsActuales.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent = "Todavía no tienes tickets. Crea uno para solicitar soporte.";
        ticketList.append(empty);
        return;
    }
    ticketsActuales.forEach((ticket) => {
        const card = document.createElement("article");
        card.className = "ticket-card";
        if (ticketsEnActualizacion.has(ticket.id)) card.classList.add("is-updating");
        if (["RESUELTO", "CERRADO"].includes(ticket.estado)) card.classList.add("status-finalized");
        else if (ticket.estado === "SOLUCIONANDO") card.classList.add("status-solving");
        else if (ticket.estado === "EN_PROCESO") card.classList.add("status-progress");
        else card.classList.add("status-pending");
        const open = document.createElement("button");
        open.className = "ticket-open";
        open.type = "button";
        const title = document.createElement("strong");
        title.textContent = ticket.titulo;
        const meta = document.createElement("span");
        meta.textContent = `${ticket.codigo} · ${etiquetaEstado(ticket.estado)} · ${ticket.prioridad} · ${ticket.departamento}${currentUserRole === "ADMIN" ? ` · ${ticket.nombre_usuario}` : ""}`;
        open.append(title, meta);
        open.addEventListener("click", () => verTicket(ticket.id));
        card.append(open);
        if (currentUserRole === "ADMIN" && !["RESUELTO", "CERRADO"].includes(ticket.estado)) {
            const actions = document.createElement("div");
            actions.className = "ticket-actions";
            [
                ["SOLUCIONANDO", "Resolviendo"],
                ["RESUELTO", "Finalizado"]
            ].forEach(([estado, label]) => {
                const action = document.createElement("button");
                action.type = "button";
                action.className = `ticket-action${ticket.estado === estado ? " active" : ""}`;
                action.textContent = label;
                action.disabled = ticketsEnActualizacion.has(ticket.id) || ticket.estado === estado;
                action.addEventListener("click", () => cambiarEstado(ticket.id, estado));
                actions.append(action);
            });
            card.append(actions);
        }
        ticketList.append(card);
    });
}

function actualizarGrafico(tickets) {
    const chart = document.querySelector("#ticket-chart");
    const legend = document.querySelector("#ticket-legend");
    const total = tickets.length;
    const hoy = fechaClave(new Date());
    const pendientes = tickets.filter((ticket) => ["ABIERTO", "EN_PROCESO", "SOLUCIONANDO", "ESPERANDO_USUARIO"].includes(ticket.estado));
    const nuevosHoy = tickets.filter((ticket) => fechaClave(new Date(ticket.created_at)) === hoy).length;
    const finalizados = tickets.filter((ticket) => ["RESUELTO", "CERRADO"].includes(ticket.estado));
    document.querySelector("#kpi-pending").textContent = String(pendientes.length);
    document.querySelector("#kpi-today").textContent = String(nuevosHoy);
    document.querySelector("#kpi-completed").textContent = String(finalizados.length);
    document.querySelector("#ticket-total").textContent = `${total} ${total === 1 ? "ticket" : "tickets"} en total`;
    legend.replaceChildren();
    let position = 0;
    const slices = estadosTicket.map((estado) => {
        const count = tickets.filter((ticket) => ticket.estado === estado.id).length;
        const end = total ? position + count / total * 100 : 0;
        const slice = `${estado.color} ${position}% ${end}%`;
        position = end;
        const item = document.createElement("li");
        const dot = document.createElement("span");
        dot.className = "legend-dot";
        dot.style.backgroundColor = estado.color;
        const label = document.createElement("span");
        label.textContent = estado.label;
        const value = document.createElement("strong");
        value.textContent = String(count);
        item.append(dot, label, value);
        legend.append(item);
        return slice;
    });
    chart.style.background = total ? `conic-gradient(${slices.join(", ")})` : "#e5e7eb";
    chart.setAttribute("aria-label", `Distribución de ${total} tickets por estado`);
    actualizarTendencia(tickets);
    actualizarPrioridades(pendientes);
}

function fechaClave(fecha) {
    return `${fecha.getFullYear()}-${fecha.getMonth()}-${fecha.getDate()}`;
}

function actualizarTendencia(tickets) {
    const container = document.querySelector("#ticket-trend");
    container.replaceChildren();
    const dias = [];
    for (let offset = 6; offset >= 0; offset -= 1) {
        const fecha = new Date();
        fecha.setHours(0, 0, 0, 0);
        fecha.setDate(fecha.getDate() - offset);
        dias.push({ fecha, clave: fechaClave(fecha), creados: 0, finalizados: 0 });
    }
    const porFecha = new Map(dias.map((dia) => [dia.clave, dia]));
    tickets.forEach((ticket) => {
        const diaCreado = porFecha.get(fechaClave(new Date(ticket.created_at)));
        if (diaCreado) diaCreado.creados += 1;
        if (ticket.resolved_at) {
            const diaFinalizado = porFecha.get(fechaClave(new Date(ticket.resolved_at)));
            if (diaFinalizado) diaFinalizado.finalizados += 1;
        }
    });
    const maximo = Math.max(1, ...dias.flatMap((dia) => [dia.creados, dia.finalizados]));
    const nombresDia = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
    dias.forEach((dia) => {
        const grupo = document.createElement("div");
        grupo.className = "trend-day";
        const barras = document.createElement("div");
        barras.className = "trend-bars";
        [[dia.creados, "created"], [dia.finalizados, "finished"]].forEach(([valor, tipo]) => {
            const barra = document.createElement("i");
            barra.className = `trend-bar ${tipo}`;
            barra.style.height = `${valor ? Math.max(5, valor / maximo * 100) : 2}%`;
            barra.title = `${valor} ${tipo === "created" ? "creados" : "finalizados"}`;
            barras.append(barra);
        });
        const etiqueta = document.createElement("small");
        etiqueta.textContent = nombresDia[dia.fecha.getDay()];
        grupo.append(barras, etiqueta);
        container.append(grupo);
    });
}

function actualizarPrioridades(pendientes) {
    const container = document.querySelector("#priority-summary");
    container.replaceChildren();
    const prioridades = [
        ["ALTA", "Alta", "high"],
        ["MEDIA", "Media", "medium"],
        ["BAJA", "Baja", "low"],
        ["CRITICA", "Crítica", "critical"]
    ];
    prioridades.forEach(([id, label, clase]) => {
        const count = pendientes.filter((ticket) => ticket.prioridad === id).length;
        const row = document.createElement("div");
        row.className = "priority-row";
        const text = document.createElement("span");
        text.textContent = label;
        const track = document.createElement("div");
        track.className = "priority-track";
        const fill = document.createElement("i");
        fill.className = clase;
        fill.style.width = `${pendientes.length ? count / pendientes.length * 100 : 0}%`;
        track.append(fill);
        const value = document.createElement("strong");
        value.textContent = String(count);
        row.append(text, track, value);
        container.append(row);
    });
}

async function cambiarEstado(ticketId, estado) {
    const anterior = ticketsActuales.find((ticket) => ticket.id === ticketId);
    if (!anterior || ticketsEnActualizacion.has(ticketId)) return;
    const estadoAnterior = anterior.estado;
    const optimista = {
        ...anterior,
        estado,
        updated_at: new Date().toISOString(),
        historial: anterior.historial || []
    };
    if (estado === "RESUELTO") {
        optimista.resolved_at = optimista.updated_at;
    }
    ticketsEnActualizacion.add(ticketId);
    ticketsActuales = ticketsActuales.map((ticket) => ticket.id === ticketId ? optimista : ticket);
    dibujarTickets();
    try {
        const actualizado = await api(`/api/tickets/${ticketId}/estado`, {
            method: "PATCH",
            body: JSON.stringify({ estado })
        });
        ticketsActuales = ticketsActuales.map((ticket) => ticket.id === ticketId ? actualizado : ticket);
        if (!ticketDetail.hidden) await verTicket(ticketId);
        notify("Estado del ticket actualizado.", "success");
    } catch (error) {
        ticketsActuales = ticketsActuales.map((ticket) => ticket.id === ticketId ? anterior : ticket);
        notify(error.message);
    } finally {
        ticketsEnActualizacion.delete(ticketId);
        dibujarTickets();
    }
}

async function verTicket(id) {
    try {
        const ticket = await api(`/api/tickets/${id}`);
        ticketDetail.replaceChildren();
        ticketDetail.hidden = false;
        const heading = document.createElement("h3");
        heading.textContent = `${ticket.codigo} · ${ticket.titulo}`;
        const desc = document.createElement("p");
        desc.textContent = ticket.descripcion;
        const info = document.createElement("p");
        info.className = "ticket-meta";
        info.textContent = `${etiquetaEstado(ticket.estado)} · ${ticket.prioridad} · ${ticket.departamento}`;
        ticketDetail.append(heading, info, desc);
        const finalizado = ["RESUELTO", "CERRADO"].includes(ticket.estado);
        if (["ADMIN", "TECNICO"].includes(currentUserRole) && !finalizado) {
            const statusForm = document.createElement("form");
            statusForm.className = "status-form";
            const status = document.createElement("select");
            estadosTicket.forEach(({ id: value, label }) => {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = label;
                option.selected = value === ticket.estado;
                status.append(option);
            });
            const update = document.createElement("button");
            update.type = "submit";
            update.className = "secondary-button";
            update.textContent = "Actualizar estado";
            statusForm.append(status, update);
            statusForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                try {
                    await api(`/api/tickets/${id}/estado`, { method: "PATCH", body: JSON.stringify({ estado: status.value }) });
                    await verTicket(id);
                    await cargarTickets();
                } catch (error) { notify(error.message); }
            });
            ticketDetail.append(statusForm);
        }
        const commentsHeading = document.createElement("h4");
        commentsHeading.textContent = "Seguimiento";
        ticketDetail.append(commentsHeading);
        ticket.comentarios.forEach((comment) => {
            const item = document.createElement("p");
            item.className = "comment-item";
            item.textContent = `${comment.nombre_usuario}: ${comment.comentario}`;
            ticketDetail.append(item);
        });
        ticket.historial.forEach((entry) => {
            const item = document.createElement("p");
            item.className = "history-item";
            const cambio = entry.estado_nuevo
                ? `: ${entry.estado_anterior || "—"} → ${entry.estado_nuevo}`
                : "";
            item.textContent = `${entry.nombre_usuario}: ${entry.accion}${cambio}`;
            ticketDetail.append(item);
        });
        if (!finalizado) {
            const form = document.createElement("form");
            form.className = "comment-form";
            const input = document.createElement("textarea");
            input.name = "comentario";
            input.placeholder = "Escribe una actualización o respuesta";
            input.required = true;
            input.maxLength = 5000;
            const submit = document.createElement("button");
            submit.className = "primary-button";
            submit.textContent = "Agregar comentario";
            form.append(input, submit);
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                try {
                    await api(`/api/tickets/${id}/comentarios`, { method: "POST", body: JSON.stringify({ comentario: input.value }) });
                    await verTicket(id);
                    await cargarTickets();
                } catch (error) { notify(error.message); }
            });
            ticketDetail.append(form);
        }
        ticketDetail.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) { notify(error.message); }
}

document.querySelector("#new-ticket-button").addEventListener("click", () => {
    ticketForm.hidden = !ticketForm.hidden;
    ticketDetail.hidden = true;
});
document.querySelector("#cancel-ticket").addEventListener("click", () => { ticketForm.reset(); ticketForm.hidden = true; });
ticketForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(ticketForm);
    const datos = Object.fromEntries(form.entries());
    datos.departamento_id = Number(datos.departamento_id);
    try {
        const ticket = await api("/api/tickets/", { method: "POST", body: JSON.stringify(datos) });
        ticketForm.reset();
        ticketForm.hidden = true;
        notify(`Ticket ${ticket.codigo} creado correctamente.`, "success");
        await cargarTickets();
        await verTicket(ticket.id);
    } catch (error) { notify(error.message); }
});
document.querySelector("#logout-button").addEventListener("click", () => {
    sessionStorage.removeItem("itdesk_token");
    window.location.replace("/login");
});

cargarUsuario();

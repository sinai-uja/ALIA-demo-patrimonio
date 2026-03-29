"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { admin, auth as authApi, ValidationError } from "@/lib/api";
import type { AdminProfileType, AdminUser, ProfileType } from "@/lib/api";

const PROFILE_BADGE_COLORS: Record<string, string> = {
  admin: "bg-red-100 text-red-700",
  investigador: "bg-blue-100 text-blue-700",
  turista: "bg-green-100 text-green-700",
  estudiante: "bg-amber-100 text-amber-700",
  profesional: "bg-purple-100 text-purple-700",
};

function getBadgeClasses(profileType: string | null): string {
  if (!profileType) return "bg-stone-100 text-stone-500";
  return PROFILE_BADGE_COLORS[profileType] ?? "bg-stone-100 text-stone-600";
}

interface EditModalProps {
  user: AdminUser;
  profileTypes: ProfileType[];
  isRootAdmin: boolean;
  onSave: (id: string, data: { password?: string | null; profile_type?: string | null }) => Promise<void>;
  onClose: () => void;
}

function EditModal({ user, profileTypes, isRootAdmin, onSave, onClose }: EditModalProps) {
  const [password, setPassword] = useState("");
  const [profileType, setProfileType] = useState(user.profile_type ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const availableTypes = isRootAdmin
    ? [{ name: "admin" } as ProfileType, ...profileTypes]
    : profileTypes.filter((pt) => pt.name !== "admin");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setFieldErrors({});
    try {
      await onSave(user.id, {
        password: password.length > 0 ? password : null,
        profile_type: profileType || null,
      });
      onClose();
    } catch (err) {
      if (err instanceof ValidationError) {
        setFieldErrors(err.fields);
      } else {
        setError(err instanceof Error ? err.message : "Error al actualizar usuario");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white p-6 shadow-xl">
        <h3 className="mb-4 text-lg font-semibold text-stone-900">
          Editar usuario: {user.username}
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="edit-password" className="block text-sm font-medium text-stone-700">
              Nueva contraseña
            </label>
            <input
              id="edit-password"
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setFieldErrors((p) => { const n = {...p}; delete n.password; return n; }); }}
              className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${fieldErrors.password ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"}`}
              placeholder="Dejar vacío para mantener la actual"
              autoComplete="new-password"
            />
            <p className="mt-1 h-4 text-xs text-red-600">{fieldErrors.password ?? ""}</p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="edit-profile" className="block text-sm font-medium text-stone-700">
              Tipo de perfil
            </label>
            <select
              id="edit-profile"
              value={profileType}
              onChange={(e) => setProfileType(e.target.value)}
              className="w-full rounded-lg border border-stone-300 px-4 py-2.5 text-stone-900 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20 capitalize"
            >
              <option value="">Sin perfil</option>
              {availableTypes.map((pt) => (
                <option key={pt.name} value={pt.name} className="capitalize">
                  {pt.name}
                </option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-stone-600 hover:bg-stone-100 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {saving ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const hydrated = useAuthStore((s) => s.hydrated);
  const profileType = useAuthStore((s) => s.profileType);
  const isRootAdmin = useAuthStore((s) => s.isRootAdmin);
  const currentUsername = useAuthStore((s) => s.username);

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [profileTypes, setProfileTypes] = useState<ProfileType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [showCreate, setShowCreate] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newProfileType, setNewProfileType] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createFieldErrors, setCreateFieldErrors] = useState<Record<string, string>>({});

  // Edit modal state
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);

  // Delete confirmation state
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Profile types panel state
  const [adminProfileTypes, setAdminProfileTypes] = useState<AdminProfileType[]>([]);
  const [newPtName, setNewPtName] = useState("");
  const [creatingPt, setCreatingPt] = useState(false);
  const [ptCreateError, setPtCreateError] = useState<string | null>(null);
  const [renamingPtId, setRenamingPtId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [ptRenameError, setPtRenameError] = useState<string | null>(null);
  const [deletingPtId, setDeletingPtId] = useState<string | null>(null);
  const [ptError, setPtError] = useState<string | null>(null);

  // Protection: redirect non-admins — wait for username to ensure fetchUser() has completed
  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) { router.replace("/"); return; }
    if (currentUsername !== null && profileType !== "admin") router.replace("/");
  }, [hydrated, isAuthenticated, currentUsername, profileType, router]);

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await admin.listUsers();
      setUsers(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar usuarios");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchProfileTypes = useCallback(async () => {
    try {
      const data = await admin.profileTypes.list();
      setAdminProfileTypes(data);
    } catch (err) {
      setPtError(err instanceof Error ? err.message : "Error al cargar tipos de perfil");
    }
  }, []);

  useEffect(() => {
    if (!hydrated || !isAuthenticated || profileType !== "admin") return;
    fetchUsers();
    fetchProfileTypes();
    authApi.getProfileTypes().then(setProfileTypes).catch(() => {});
  }, [hydrated, isAuthenticated, profileType, fetchUsers, fetchProfileTypes]);

  const availableCreateTypes = isRootAdmin
    ? [{ name: "admin" } as ProfileType, ...profileTypes]
    : profileTypes.filter((pt) => pt.name !== "admin");

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!newUsername.trim()) errs.username = "El nombre de usuario no puede estar vacío";
    if (!newPassword.trim()) errs.password = "La contraseña no puede estar vacía";
    if (Object.keys(errs).length > 0) { setCreateFieldErrors(errs); return; }
    setCreating(true);
    setCreateError(null);
    setCreateFieldErrors({});
    try {
      await admin.createUser({
        username: newUsername,
        password: newPassword,
        profile_type: newProfileType || null,
      });
      setNewUsername("");
      setNewPassword("");
      setNewProfileType("");
      setShowCreate(false);
      await fetchUsers();
      await fetchProfileTypes();
    } catch (err) {
      if (err instanceof ValidationError) {
        setCreateFieldErrors(err.fields);
      } else {
        setCreateError(err instanceof Error ? err.message : "Error al crear usuario");
      }
    } finally {
      setCreating(false);
    }
  }

  async function handleEditSave(id: string, data: { password?: string | null; profile_type?: string | null }) {
    await admin.updateUser(id, data);
    await fetchUsers();
    await fetchProfileTypes();
  }

  async function handleDelete(id: string) {
    try {
      await admin.deleteUser(id);
      setDeletingId(null);
      await fetchUsers();
      await fetchProfileTypes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar usuario");
      setDeletingId(null);
    }
  }

  async function handleCreatePt(e: React.FormEvent) {
    e.preventDefault();
    const name = newPtName.trim();
    if (!name) { setPtCreateError("El nombre no puede estar vacío"); return; }
    setCreatingPt(true);
    setPtCreateError(null);
    try {
      await admin.profileTypes.create(name);
      setNewPtName("");
      await fetchProfileTypes();
      authApi.getProfileTypes().then(setProfileTypes).catch(() => {});
    } catch (err) {
      setPtCreateError(err instanceof Error ? err.message : "Error al crear tipo de perfil");
    } finally {
      setCreatingPt(false);
    }
  }

  async function handleRenamePt(id: string) {
    const name = renameDraft.trim();
    if (!name) { setPtRenameError("El nombre no puede estar vacío"); return; }
    setPtRenameError(null);
    try {
      await admin.profileTypes.rename(id, name);
      setRenamingPtId(null);
      setRenameDraft("");
      await fetchProfileTypes();
      authApi.getProfileTypes().then(setProfileTypes).catch(() => {});
    } catch (err) {
      setPtRenameError(err instanceof Error ? err.message : "Error al renombrar");
    }
  }

  async function handleDeletePt(id: string) {
    setPtError(null);
    try {
      await admin.profileTypes.delete(id);
      setDeletingPtId(null);
      await fetchProfileTypes();
      authApi.getProfileTypes().then(setProfileTypes).catch(() => {});
    } catch (err) {
      setPtError(err instanceof Error ? err.message : "Error al eliminar tipo de perfil");
      setDeletingPtId(null);
    }
  }

  function canEditUser(user: AdminUser): boolean {
    // Root admin can edit everyone except themselves
    if (isRootAdmin) {
      return user.username !== currentUsername;
    }
    // Regular admin can only edit non-admin users
    return user.profile_type !== "admin";
  }

  if (!hydrated || !isAuthenticated || profileType !== "admin") {
    return null;
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left panel — users */}
        <div className="lg:col-span-2 space-y-8">
          {/* Header */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h1 className="text-2xl font-bold tracking-tight text-stone-900">
              Gestión de usuarios
            </h1>
            <button
              onClick={() => setShowCreate((prev) => !prev)}
              className="self-start sm:self-auto rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800"
            >
              {showCreate ? "Cancelar" : "Nuevo usuario"}
            </button>
          </div>

          {/* Create form */}
          {showCreate && (
            <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-stone-800">Crear usuario</h2>
              <form onSubmit={handleCreate} noValidate className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-1.5">
                    <label htmlFor="create-username" className="block text-sm font-medium text-stone-700">
                      Usuario
                    </label>
                    <input
                      id="create-username"
                      type="text"
                      value={newUsername}
                      onChange={(e) => { setNewUsername(e.target.value); setCreateFieldErrors((p) => { const n = {...p}; delete n.username; return n; }); }}
                      className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${createFieldErrors.username ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"}`}
                      placeholder="Nombre de usuario"
                      autoComplete="off"
                    />
                    <p className="mt-1 h-4 text-xs text-red-600">{createFieldErrors.username ?? ""}</p>
                  </div>
                  <div className="space-y-1.5">
                    <label htmlFor="create-password" className="block text-sm font-medium text-stone-700">
                      Contraseña
                    </label>
                    <input
                      id="create-password"
                      type="password"
                      value={newPassword}
                      onChange={(e) => { setNewPassword(e.target.value); setCreateFieldErrors((p) => { const n = {...p}; delete n.password; return n; }); }}
                      className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${createFieldErrors.password ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"}`}
                      placeholder="Contraseña"
                      autoComplete="new-password"
                    />
                    <p className="mt-1 h-4 text-xs text-red-600">{createFieldErrors.password ?? ""}</p>
                  </div>
                  <div className="space-y-1.5">
                    <label htmlFor="create-profile" className="block text-sm font-medium text-stone-700">
                      Tipo de perfil
                    </label>
                    <select
                      id="create-profile"
                      value={newProfileType}
                      onChange={(e) => setNewProfileType(e.target.value)}
                      className="w-full rounded-lg border border-stone-300 px-4 py-2.5 text-stone-900 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20 capitalize"
                    >
                      <option value="">Sin perfil</option>
                      {availableCreateTypes.map((pt) => (
                        <option key={pt.name} value={pt.name} className="capitalize">
                          {pt.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {createError && <p className="text-sm text-red-600">{createError}</p>}

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={creating}
                    className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {creating ? "Creando..." : "Crear usuario"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Users table */}
          <div className="rounded-xl border border-stone-200 bg-white shadow-sm overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-green-600" />
                <span className="ml-3 text-sm text-stone-500">Cargando usuarios...</span>
              </div>
            ) : users.length === 0 ? (
              <div className="py-16 text-center text-sm text-stone-500">
                No hay usuarios registrados
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-stone-200 bg-stone-50">
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-stone-500">
                      Usuario
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-stone-500">
                      Perfil
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-stone-500">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {users.map((user) => {
                    const editable = canEditUser(user);
                    const isDeleting = deletingId === user.id;

                    return (
                      <tr key={user.id} className="hover:bg-stone-50/50 transition-colors">
                        <td className="px-6 py-4 text-sm font-medium text-stone-900">
                          {user.username}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${getBadgeClasses(user.profile_type)}`}
                          >
                            {user.profile_type ?? "sin perfil"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          {editable && !isDeleting && (
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => setEditingUser(user)}
                                className="rounded-lg p-1.5 text-stone-400 hover:text-green-700 hover:bg-green-50 transition-colors"
                                title="Editar usuario"
                              >
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                              </button>
                              <button
                                onClick={() => setDeletingId(user.id)}
                                className="rounded-lg p-1.5 text-stone-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                                title="Eliminar usuario"
                              >
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </div>
                          )}
                          {isDeleting && (
                            <div className="flex items-center justify-end gap-2">
                              <span className="text-xs text-stone-500">Confirmar eliminación?</span>
                              <button
                                onClick={() => handleDelete(user.id)}
                                className="rounded-lg px-2.5 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 transition-colors"
                              >
                                Eliminar
                              </button>
                              <button
                                onClick={() => setDeletingId(null)}
                                className="rounded-lg px-2.5 py-1 text-xs font-medium text-stone-600 hover:bg-stone-100 transition-colors"
                              >
                                Cancelar
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Edit modal */}
          {editingUser && (
            <EditModal
              user={editingUser}
              profileTypes={profileTypes}
              isRootAdmin={isRootAdmin}
              onSave={handleEditSave}
              onClose={() => setEditingUser(null)}
            />
          )}
        </div>

        {/* Right panel — profile types */}
        <div className="space-y-8">
          <h2 className="text-2xl font-bold tracking-tight text-stone-900">Tipos de perfil</h2>
          <div className="rounded-xl border border-stone-200 bg-white shadow-sm overflow-hidden">
            {/* Create form */}
            <div className="px-5 py-4 border-b border-stone-100">
              <form onSubmit={handleCreatePt} noValidate className="flex gap-2">
                <input
                  value={newPtName}
                  onChange={(e) => { setNewPtName(e.target.value); setPtCreateError(null); }}
                  placeholder="Nuevo tipo..."
                  className="flex-1 min-w-0 rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
                />
                <button
                  type="submit"
                  disabled={creatingPt}
                  className="shrink-0 rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-3 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {creatingPt ? "..." : "Añadir"}
                </button>
              </form>
              <p className="mt-1 h-4 text-xs text-red-600">{ptCreateError ?? ""}</p>
            </div>

            {/* Profile type list */}
            {adminProfileTypes.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-stone-400">No hay tipos de perfil</p>
            ) : (
              <ul className="divide-y divide-stone-100">
                {adminProfileTypes.map((pt) => {
                  const isAdmin = pt.name === "admin";
                  const isRenaming = renamingPtId === pt.id;
                  const isDeleting = deletingPtId === pt.id;
                  return (
                    <li key={pt.id} className="px-5 py-3">
                      {isRenaming ? (
                        <div className="space-y-2">
                          <div className="flex gap-2">
                            <input
                              autoFocus
                              value={renameDraft}
                              onChange={(e) => { setRenameDraft(e.target.value); setPtRenameError(null); }}
                              onKeyDown={(e) => { if (e.key === "Escape") { setRenamingPtId(null); setPtRenameError(null); } }}
                              className="flex-1 min-w-0 rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-900 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
                            />
                            <button
                              onClick={() => handleRenamePt(pt.id)}
                              className="shrink-0 rounded-lg bg-green-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-green-700 transition-colors"
                            >
                              Guardar
                            </button>
                            <button
                              onClick={() => { setRenamingPtId(null); setPtRenameError(null); }}
                              className="shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-600 hover:bg-stone-100 transition-colors"
                            >
                              Cancelar
                            </button>
                          </div>
                          <p className="h-4 text-xs text-red-600">{ptRenameError ?? ""}</p>
                        </div>
                      ) : isDeleting ? (
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs text-stone-500 flex-1">¿Eliminar <span className="font-medium capitalize">{pt.name}</span>?</span>
                          <button
                            onClick={() => handleDeletePt(pt.id)}
                            className="rounded-lg px-2.5 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 transition-colors"
                          >
                            Eliminar
                          </button>
                          <button
                            onClick={() => setDeletingPtId(null)}
                            className="rounded-lg px-2.5 py-1 text-xs font-medium text-stone-600 hover:bg-stone-100 transition-colors"
                          >
                            Cancelar
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize shrink-0 ${getBadgeClasses(pt.name)}`}>
                              {pt.name}
                            </span>
                            <span className="text-xs text-stone-400 whitespace-nowrap">
                              {pt.user_count} {pt.user_count === 1 ? "usuario" : "usuarios"}
                            </span>
                          </div>
                          {!isAdmin && (
                            <div className="flex items-center gap-1 shrink-0">
                              <button
                                onClick={() => { setRenamingPtId(pt.id); setRenameDraft(pt.name); setPtRenameError(null); }}
                                className="rounded-lg p-1.5 text-stone-400 hover:text-green-700 hover:bg-green-50 transition-colors"
                                title="Renombrar"
                              >
                                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                              </button>
                              <button
                                onClick={() => setDeletingPtId(pt.id)}
                                className="rounded-lg p-1.5 text-stone-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                                title="Eliminar"
                              >
                                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}

            {/* Error banner */}
            {ptError && (
              <div className="border-t border-stone-100 px-5 py-3 text-sm text-red-600">
                {ptError}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import { admin, auth as authApi, ValidationError } from "@/lib/api";
import { minDelay } from "@/lib/minDelay";
import DeleteConfirmModal from "@/components/shared/DeleteConfirmModal";
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-5 text-base font-semibold text-stone-900">
          Editar: {user.username}
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

  // Delete modal state
  const [deletingUser, setDeletingUser] = useState<AdminUser | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteInProgress, setDeleteInProgress] = useState(false);

  // Profile types panel state
  const [adminProfileTypes, setAdminProfileTypes] = useState<AdminProfileType[]>([]);
  const [newPtName, setNewPtName] = useState("");
  const [creatingPt, setCreatingPt] = useState(false);
  const [ptCreateError, setPtCreateError] = useState<string | null>(null);
  const [renamingPtId, setRenamingPtId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [ptRenameError, setPtRenameError] = useState<string | null>(null);
  const [deletingPt, setDeletingPt] = useState<AdminProfileType | null>(null);
  const [showCreatePt, setShowCreatePt] = useState(false);
  const [ptError, setPtError] = useState<string | null>(null);

  // Protection: redirect non-admins — wait for username to ensure fetchUser() has completed
  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) { router.replace("/"); return; }
    if (currentUsername !== null && profileType !== "admin") router.replace("/");
  }, [hydrated, isAuthenticated, currentUsername, profileType, router]);

  const fetchUsers = useCallback(async () => {
    try {
      const data = await admin.listUsers();
      setUsers(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar usuarios");
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
    setLoading(true);
    minDelay(Promise.all([
      fetchUsers(),
      fetchProfileTypes(),
      authApi.getProfileTypes().then(setProfileTypes).catch(() => {}),
    ])).finally(() => setLoading(false));
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

  async function handleDelete() {
    if (!deletingUser) return;
    setDeleteInProgress(true);
    setDeleteError(null);
    try {
      await admin.deleteUser(deletingUser.id);
      setDeletingUser(null);
      await fetchUsers();
      await fetchProfileTypes();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Error al eliminar usuario");
    } finally {
      setDeleteInProgress(false);
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
      setShowCreatePt(false);
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

  async function handleDeletePt() {
    if (!deletingPt) return;
    setDeleteInProgress(true);
    setDeleteError(null);
    try {
      await admin.profileTypes.delete(deletingPt.id);
      setDeletingPt(null);
      await fetchProfileTypes();
      authApi.getProfileTypes().then(setProfileTypes).catch(() => {});
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Error al eliminar tipo de perfil");
    } finally {
      setDeleteInProgress(false);
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

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-3.625rem)] gap-3">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-green-600" />
        <span className="text-sm text-stone-400">Cargando panel de administración...</span>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      {/* Admin navigation tabs */}
      <div className="mb-6 flex items-center gap-1">
        <span className="rounded-lg bg-green-50 px-4 py-1.5 text-sm font-medium text-green-800">
          Gestion de usuarios
        </span>
        <Link
          href="/admin/traces"
          className="rounded-lg px-4 py-1.5 text-sm font-medium text-stone-500 hover:text-stone-800 hover:bg-stone-100 transition-colors"
        >
          Trazabilidad
        </Link>
      </div>

      <div className="grid gap-8 lg:grid-cols-3 items-start">

        {/* ── Left panel — Users ── */}
        <div className="lg:col-span-2 rounded-xl border border-stone-200/60 bg-white shadow-sm overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-stone-200">
            <h1 className="text-sm font-semibold text-stone-900">Usuarios</h1>
            <button
              onClick={() => setShowCreate(true)}
              className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800"
            >
              Nuevo usuario
            </button>
          </div>

          {error && (
            <div className="border-b border-red-100 bg-red-50 px-5 py-2.5 text-xs text-red-700">
              {error}
            </div>
          )}

          {/* Table */}
          {users.length === 0 ? (
            <div className="py-16 text-center text-sm text-stone-400">
              No hay usuarios registrados
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-stone-200 bg-stone-50">
                  <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">
                    Usuario
                  </th>
                  <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">
                    Perfil
                  </th>
                  <th className="px-5 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-stone-400">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {users.map((user) => {
                  const editable = canEditUser(user);
                  return (
                    <tr key={user.id} className="hover:bg-stone-50/50 transition-colors">
                      <td className="px-5 py-3">
                        <span className="text-sm font-medium text-stone-900">{user.username}</span>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${getBadgeClasses(user.profile_type)}`}>
                          {user.profile_type ?? "sin perfil"}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right">
                        {editable && (
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => setEditingUser(user)} className="rounded-lg p-1.5 text-stone-400 hover:text-green-700 hover:bg-green-50 transition-colors" title="Editar">
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                              </svg>
                            </button>
                            <button onClick={() => setDeletingUser(user)} className="rounded-lg p-1.5 text-stone-400 hover:text-red-600 hover:bg-red-50 transition-colors" title="Eliminar">
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
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

        {/* ── Right panel — Profile types ── */}
        <div className="rounded-xl border border-stone-200/60 bg-white shadow-sm overflow-hidden">
          {/* Header — same pattern as users */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-stone-200">
            <h2 className="text-sm font-semibold text-stone-900">Tipos de perfil</h2>
            <button
              onClick={() => setShowCreatePt(true)}
              className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800"
            >
              Añadir
            </button>
          </div>

          {ptError && (
            <div className="border-b border-red-100 bg-red-50 px-5 py-2.5 text-xs text-red-700">
              {ptError}
            </div>
          )}

          {/* Table */}
          {adminProfileTypes.length === 0 ? (
            <div className="py-16 text-center text-sm text-stone-400">No hay tipos de perfil</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-stone-200 bg-stone-50">
                  <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">
                    Nombre
                  </th>
                  <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">
                    Usuarios
                  </th>
                  <th className="px-5 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-stone-400">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {adminProfileTypes.map((pt) => {
                  const isAdmin = pt.name === "admin";
                  return (
                    <tr key={pt.id} className="hover:bg-stone-50/50 transition-colors">
                      <td className="px-5 py-3">
                        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${getBadgeClasses(pt.name)}`}>
                          {pt.name}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-xs text-stone-500 tabular-nums">
                        {pt.user_count}
                      </td>
                      <td className="px-5 py-3 text-right">
                        {!isAdmin && (
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => { setRenamingPtId(pt.id); setRenameDraft(pt.name); setPtRenameError(null); }} className="rounded-lg p-1.5 text-stone-400 hover:text-green-700 hover:bg-green-50 transition-colors" title="Renombrar">
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                              </svg>
                            </button>
                            <button onClick={() => setDeletingPt(pt)} className="rounded-lg p-1.5 text-stone-400 hover:text-red-600 hover:bg-red-50 transition-colors" title="Eliminar">
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
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
      </div>

      {/* ── Modals ── */}

      {/* Create user modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowCreate(false)}>
          <div className="w-full max-w-lg rounded-2xl border border-stone-200/60 bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-5 text-base font-semibold text-stone-900">Nuevo usuario</h3>
            <form onSubmit={handleCreate} noValidate className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="create-username" className="block text-sm font-medium text-stone-700">Usuario</label>
                <input
                  id="create-username" type="text" value={newUsername} autoComplete="off" placeholder="Nombre de usuario"
                  onChange={(e) => { setNewUsername(e.target.value); setCreateFieldErrors((p) => { const n = {...p}; delete n.username; return n; }); }}
                  className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${createFieldErrors.username ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"}`}
                />
                <p className="h-4 text-xs text-red-600">{createFieldErrors.username ?? ""}</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="create-password" className="block text-sm font-medium text-stone-700">Contraseña</label>
                  <input
                    id="create-password" type="password" value={newPassword} autoComplete="new-password" placeholder="Contraseña"
                    onChange={(e) => { setNewPassword(e.target.value); setCreateFieldErrors((p) => { const n = {...p}; delete n.password; return n; }); }}
                    className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${createFieldErrors.password ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"}`}
                  />
                  <p className="h-4 text-xs text-red-600">{createFieldErrors.password ?? ""}</p>
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="create-profile" className="block text-sm font-medium text-stone-700">Tipo de perfil</label>
                  <select
                    id="create-profile" value={newProfileType} onChange={(e) => setNewProfileType(e.target.value)}
                    className="w-full rounded-lg border border-stone-300 px-4 py-2.5 text-stone-900 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20 capitalize"
                  >
                    <option value="">Sin perfil</option>
                    {availableCreateTypes.map((pt) => (
                      <option key={pt.name} value={pt.name} className="capitalize">{pt.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              {createError && <p className="text-sm text-red-600">{createError}</p>}
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg px-4 py-2 text-sm font-medium text-stone-600 hover:bg-stone-100 transition-colors">Cancelar</button>
                <button type="submit" disabled={creating} className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800 disabled:opacity-60 disabled:cursor-not-allowed">
                  {creating ? "Creando..." : "Crear usuario"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create profile type modal */}
      {showCreatePt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowCreatePt(false)}>
          <div className="w-full max-w-sm rounded-2xl border border-stone-200/60 bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-5 text-base font-semibold text-stone-900">Nuevo tipo de perfil</h3>
            <form onSubmit={handleCreatePt} noValidate className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="create-pt-name" className="block text-sm font-medium text-stone-700">Nombre</label>
                <input
                  id="create-pt-name" type="text" value={newPtName} placeholder="Ej: investigador"
                  onChange={(e) => { setNewPtName(e.target.value); setPtCreateError(null); }}
                  className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${ptCreateError ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"}`}
                />
                <p className="h-4 text-xs text-red-600">{ptCreateError ?? ""}</p>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowCreatePt(false)} className="rounded-lg px-4 py-2 text-sm font-medium text-stone-600 hover:bg-stone-100 transition-colors">Cancelar</button>
                <button type="submit" disabled={creatingPt} className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800 disabled:opacity-60 disabled:cursor-not-allowed">
                  {creatingPt ? "Creando..." : "Añadir"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Rename profile type modal */}
      {renamingPtId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => { setRenamingPtId(null); setPtRenameError(null); }}>
          <div className="w-full max-w-sm rounded-2xl border border-stone-200/60 bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-5 text-base font-semibold text-stone-900">Renombrar tipo de perfil</h3>
            <form onSubmit={(e) => { e.preventDefault(); handleRenamePt(renamingPtId); }} noValidate className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="rename-pt-name" className="block text-sm font-medium text-stone-700">Nuevo nombre</label>
                <input
                  id="rename-pt-name" type="text" autoFocus value={renameDraft} placeholder="Nombre del tipo"
                  onChange={(e) => { setRenameDraft(e.target.value); setPtRenameError(null); }}
                  className={`w-full rounded-lg border px-4 py-2.5 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 transition-colors ${ptRenameError ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-stone-300 focus:border-green-600 focus:ring-green-600/20"}`}
                />
                <p className="h-4 text-xs text-red-600">{ptRenameError ?? ""}</p>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => { setRenamingPtId(null); setPtRenameError(null); }} className="rounded-lg px-4 py-2 text-sm font-medium text-stone-600 hover:bg-stone-100 transition-colors">Cancelar</button>
                <button type="submit" className="rounded-lg bg-gradient-to-r from-green-600 to-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:from-green-700 hover:to-emerald-800">
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit user modal */}
      {editingUser && (
        <EditModal
          user={editingUser}
          profileTypes={profileTypes}
          isRootAdmin={isRootAdmin}
          onSave={handleEditSave}
          onClose={() => setEditingUser(null)}
        />
      )}

      {/* Delete user modal */}
      {deletingUser && (
        <DeleteConfirmModal
          title="Eliminar usuario"
          entityName={deletingUser.username}
          onConfirm={handleDelete}
          onCancel={() => { setDeletingUser(null); setDeleteError(null); }}
          deleting={deleteInProgress}
          error={deleteError}
        />
      )}

      {/* Delete profile type modal */}
      {deletingPt && (
        <DeleteConfirmModal
          title="Eliminar tipo de perfil"
          entityName={deletingPt.name}
          onConfirm={handleDeletePt}
          onCancel={() => { setDeletingPt(null); setDeleteError(null); }}
          deleting={deleteInProgress}
          error={deleteError}
        />
      )}
    </div>
  );
}

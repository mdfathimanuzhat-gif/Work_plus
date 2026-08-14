import api from "./api.js";

export function login(email, password) {
  return api.post("/auth/login", { email, password });
}

export function logout(refreshToken) {
  return api.post("/auth/logout", { refresh_token: refreshToken });
}

export function getMe() {
  return api.get("/auth/me");
}

export function getMyProfile() {
  return api.get("/employees/me");
}

export function listEmployees(params) {
  return api.get("/employees", { params });
}

export function getEmployee(id) {
  return api.get(`/employees/${id}`);
}

export function createEmployee(payload) {
  return api.post("/employees", payload);
}

export function updateEmployee(id, payload) {
  return api.patch(`/employees/${id}`, payload);
}

export function deactivateEmployee(id) {
  return api.post(`/employees/${id}/deactivate`);
}

export function listDepartments() {
  return api.get("/departments");
}

export function createDepartment(payload) {
  return api.post("/departments", payload);
}

export function updateDepartment(id, payload) {
  return api.patch(`/departments/${id}`, payload);
}

export function listTeams() {
  return api.get("/teams");
}

export function getTeam(id) {
  return api.get(`/teams/${id}`);
}

export function createTeam(payload) {
  return api.post("/teams", payload);
}

export function updateTeam(id, payload) {
  return api.patch(`/teams/${id}`, payload);
}

export function listTeamMembers(id) {
  return api.get(`/teams/${id}/members`);
}

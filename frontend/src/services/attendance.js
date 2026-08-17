import api from "./api.js";

export function getMyAttendance(params) {
  return api.get("/attendance/me", { params });
}

export function getMyAttendanceOnDate(attendanceDate) {
  return api.get(`/attendance/me/${attendanceDate}`);
}

export function getMyLiveAttendance() {
  return api.get("/attendance/me/live");
}

export function getTeamAttendance(attendanceDate) {
  return api.get(`/attendance/team/${attendanceDate}`);
}

export function getEmployeeAttendance(employeeId, attendanceDate) {
  return api.get(`/attendance/${employeeId}/${attendanceDate}`);
}

export async function getMyAttendanceLive() {
  const response = await getMyLiveAttendance();
  return response.data;
}

export async function getMyAttendanceDay(attendanceDate) {
  const response = await getMyAttendanceOnDate(attendanceDate);
  return response.data;
}

export function getMyAttendanceEvents(attendanceDate) {
  return api.get("/attendance/me/events", { params: { date: attendanceDate } });
}

function asEventList(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  if (Array.isArray(payload.events)) return payload.events;
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.data)) return payload.data;
  return [];
}

export async function getEvents(date) {
  const response = await getMyAttendanceEvents(date);
  return asEventList(response?.data);
}

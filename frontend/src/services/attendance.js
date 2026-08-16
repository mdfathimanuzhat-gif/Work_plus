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

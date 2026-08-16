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

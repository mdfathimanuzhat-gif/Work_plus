import api from "./api.js";

export function createTimesheetEntry(payload) {
  return api.post("/timesheet/entries", payload);
}

export function listMyTimesheetEntries(params) {
  return api.get("/timesheet/entries", { params });
}

export function submitTimesheetEntry(timesheetId) {
  return api.post(`/timesheet/entries/${timesheetId}/submit`);
}

export function listTeamTimesheetEntries() {
  return api.get("/timesheet/team");
}

export function reviewTimesheetEntry(timesheetId, payload) {
  return api.post(`/timesheet/entries/${timesheetId}/review`, payload);
}

export function getTimesheetEntry(timesheetId) {
  return api.get(`/timesheet/entries/${timesheetId}`);
}

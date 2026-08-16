import EmptyState from "./EmptyState.jsx";

export default function DataTable({ columns, rows, empty, emptyTitle, emptyBody }) {
  if (!rows?.length) {
    return empty || <EmptyState title={emptyTitle || "No records yet."} message={emptyBody} />;
  }
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.id || row.attendance_date || index}>
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

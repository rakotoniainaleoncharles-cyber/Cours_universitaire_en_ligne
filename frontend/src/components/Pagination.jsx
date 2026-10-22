export default function Pagination({ page, pageSize, total, onPageChange }) {
  const pageCount = Math.ceil(total / pageSize)
  if (pageCount <= 1) return null

  return (
    <div className="list-pagination">
      <span>{(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} sur {total}</span>
      <div>
        <button type="button" className="secondary-button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Précédent</button>
        <span>Page {page} / {pageCount}</span>
        <button type="button" className="secondary-button" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>Suivant</button>
      </div>
    </div>
  )
}

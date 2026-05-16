import type { FormEvent } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../styles/components/SearchBar.css";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();

    if (!query.trim()) return;

    navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <form className="search-container" onSubmit={handleSearch}>
      <input
        className="search-input"
        type="text"
        placeholder="Tìm kiếm quần áo..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <button className="search-button" type="submit">
        Tìm
      </button>
    </form>
  );
}
import React, { useState, useEffect, useRef } from "react";
import "./MultiSelect.css";

export default function MultiSelect({
  options = [],
  selected = [],
  onChange,
  placeholder = "Select roles..."
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const containerRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleToggleOption = (option) => {
    let updated;
    if (selected.includes(option)) {
      updated = selected.filter((item) => item !== option);
    } else {
      updated = [...selected, option];
    }
    onChange(updated);
  };

  const handleRemoveSelected = (e, option) => {
    e.stopPropagation();
    onChange(selected.filter((item) => item !== option));
  };

  const handleClearAll = (e) => {
    e.stopPropagation();
    onChange([]);
  };

  const handleSelectAll = (e) => {
    e.stopPropagation();
    // Select all filtered options, or all options?
    // Select all available options
    onChange([...options]);
  };

  const filteredOptions = options.filter((option) =>
    option.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="multiselect-container" ref={containerRef}>
      <div
        className={`multiselect-trigger ${isOpen ? "open" : ""}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="multiselect-values">
          {selected.length === 0 ? (
            <span className="multiselect-placeholder">{placeholder}</span>
          ) : (
            selected.map((val) => (
              <span key={val} className="multiselect-tag">
                {val}
                <button
                  type="button"
                  className="multiselect-tag-remove"
                  onClick={(e) => handleRemoveSelected(e, val)}
                >
                  &times;
                </button>
              </span>
            ))
          )}
        </div>
        <div className="multiselect-actions">
          {selected.length > 0 && (
            <button
              type="button"
              className="multiselect-clear-btn"
              onClick={handleClearAll}
              title="Clear all"
            >
              &times;
            </button>
          )}
          <span className="multiselect-arrow"></span>
        </div>
      </div>

      {isOpen && (
        <div className="multiselect-dropdown">
          <div className="multiselect-search-container">
            <input
              type="text"
              className="multiselect-search-input"
              placeholder="Search roles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              autoFocus
            />
          </div>
          
          <div className="multiselect-bulk-actions">
            <button
              type="button"
              className="multiselect-bulk-btn"
              onClick={handleSelectAll}
            >
              Select All
            </button>
            <button
              type="button"
              className="multiselect-bulk-btn"
              onClick={handleClearAll}
              disabled={selected.length === 0}
            >
              Clear All
            </button>
          </div>

          <div className="multiselect-options-list">
            {filteredOptions.length === 0 ? (
              <div className="multiselect-no-options">No roles found</div>
            ) : (
              filteredOptions.map((option) => {
                const isChecked = selected.includes(option);
                return (
                  <label
                    key={option}
                    className={`multiselect-option-item ${
                      isChecked ? "selected" : ""
                    }`}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => handleToggleOption(option)}
                    />
                    <span>{option}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

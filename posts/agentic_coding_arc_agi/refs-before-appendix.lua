-- Pandoc Lua filter: move the bibliography (Div with id "refs") 
-- so it appears before the Appendix section.
--
-- Citeproc places the bibliography at the end of the document.
-- This filter relocates it to just before the first Header whose
-- text starts with "Appendix".

function Pandoc(doc)
  local dominated_by_refs = false  -- trailing blocks after refs div
  local refs_block = nil
  local before = pandoc.List()
  local appendix_idx = nil

  -- First pass: find the Appendix header index
  for i, block in ipairs(doc.blocks) do
    if block.t == "Header" then
      local text = pandoc.utils.stringify(block)
      if text:match("^Appendix") then
        appendix_idx = i
        break
      end
    end
  end

  if appendix_idx == nil then
    -- No Appendix section found; nothing to do
    return doc
  end

  -- Second pass: collect refs div and everything else
  local refs_blocks = pandoc.List()
  local other_blocks = pandoc.List()
  local in_refs = false

  for i, block in ipairs(doc.blocks) do
    if block.t == "Div" and block.identifier == "refs" then
      refs_blocks:insert(block)
    else
      other_blocks:insert(block)
    end
  end

  if #refs_blocks == 0 then
    return doc
  end

  -- Rebuild: everything before appendix, then refs, then appendix onwards
  local result = pandoc.List()
  local found_appendix = false

  for _, block in ipairs(other_blocks) do
    if not found_appendix and block.t == "Header" then
      local text = pandoc.utils.stringify(block)
      if text:match("^Appendix") then
        -- Insert refs blocks here, before Appendix
        for _, rb in ipairs(refs_blocks) do
          result:insert(rb)
        end
        found_appendix = true
      end
    end
    result:insert(block)
  end

  -- If appendix was never found (shouldn't happen), append refs at end
  if not found_appendix then
    for _, rb in ipairs(refs_blocks) do
      result:insert(rb)
    end
  end

  doc.blocks = result
  return doc
end


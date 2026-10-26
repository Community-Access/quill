-- Give Studio's specification tables explicit captions and header associations.
local section = "QUILL Studio requirements"

return {{
  traverse = "topdown",
  Header = function(el)
    section = pandoc.utils.stringify(el.content)
  end,
  Table = function(el)
    if #el.caption.long == 0 then
      el.caption.long = {pandoc.Plain({pandoc.Str("Table: " .. section)})}
    end
    for _, row in ipairs(el.head.rows) do
      for _, cell in ipairs(row.cells) do
        cell.attr.attributes["scope"] = "col"
      end
    end
    for _, body in ipairs(el.bodies) do
      body.row_head_columns = 1
      for _, row in ipairs(body.body) do
        if row.cells[1] then
          row.cells[1].attr.attributes["scope"] = "row"
        end
      end
    end
    return el
  end
}}

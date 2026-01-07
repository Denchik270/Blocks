# заполнить строку y=5 полностью нулями в grid, но пометить все клетки как невидимые

y = 5
for x in range(self.GRID_WIDTH):
    self.grid[y][x] = 0   # или 0/None — не важно, невидимость учтётся
    self._invisible_cells.add((x, y))

print("Before clear:", any(any(row) for row in self.grid), "invisibles:", len(self._invisible_cells))
self.clear_lines()
print("After clear: first rows:", self.grid[:3])
print("Invisibles after:", self._invisible_cells)
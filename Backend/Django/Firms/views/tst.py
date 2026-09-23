total_firms = 451
batch_size = 5
batches = [(i, min(i + batch_size, total_firms)) for i in range(0, total_firms, batch_size)]
print(batches)
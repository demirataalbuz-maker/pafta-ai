# -*- coding: utf-8 -*-
"""ai-uretim-08 gerçek deneyinin gloo işçisi: bir rank gibi süreç grubuna katılır, kendi gradyanını all_reduce eder.
    python ai_uretim_08_isci.py <rank> <dunya> <depo_dosyasi> <giris.pt> <cikis.pt>
"""
import sys

import torch
import torch.distributed as dist


def main():
    rank, dunya, depo, giris, cikis = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
    dist.init_process_group("gloo", store=dist.FileStore(depo, dunya), rank=rank, world_size=dunya)
    t = torch.load(giris)[rank].clone()
    dist.all_reduce(t, op=dist.ReduceOp.SUM)
    torch.save({"rank": rank, "toplam": t, "backend": dist.get_backend()}, cikis)
    dist.destroy_process_group()


if __name__ == "__main__":
    main()

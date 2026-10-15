# Courtroom V4

The reward audit rejected production proxy shaping: 143/143 originally valid corrupted argument transitions retained the same old reward, and the replacement assessor failed label-injection stress (54/80 correct to 39/80). The existing GAE already propagated terminal credit through 431/431 audited request decisions. Therefore V4 keeps global-time GAE and terminal +/-1, plus step .01/output-token .00001/invalid .1 costs. It does not introduce another unvalidated scorer.

The actor reads frozen pinned BGE768 embeddings of source, hypothesis/claim content and recent public dialogue, with explicit label, author, status and budget features. Per-role attention128/4heads chooses an action and an eligible existing claim/hypothesis target. PPO uses the joint action/target probability and stored masks. LLM writes grounded arguments, proposes labels for new hypotheses and decides the final verdict. Concession reasons reach Judge. Grounding still resolves source evidence IDs; gold and rewards are excluded from policy/LLM input.

Train uses official3168 classification examples. Development uses the exact dialectical66 diagnostic cases selected from official test errors. These are exposed development examples, not fresh held-out test. V3 best checkpoint measured 17/66 correct (25.76%) and macro-F1 .247 on this set; older dev64 results are not comparable. V4 superiority requires actual training and evaluation; a small pilot verifies execution only.

CPU command:
```powershell
.venv\Scripts\python.exe -u -m src.courtroom_rl.runner train --config configs/courtroom_rl.v4.yaml --epochs 1 --batch-size 8 --dev-every 10 --warmup-episodes 8 --seed 0 --log-steps
```
Kaggle uses configs/courtroom_rl.v4.kaggle.yaml and the one-cell instructions in kaggle-github.md. CUDA actor/critic/BGE does not accelerate the remote LLM API, which dominates runtime.

Resume uses the same command plus --resume PATH_TO_LAST_PT, with --epochs specifying the total target. Restore the entire run directory to retain best.pt. Source/config/data/dev/model/device must match; V3 checkpoints cannot initialize V4. Full optimizer and Python/NumPy/CPU/CUDA RNG are restored. Replay verifies target masks and transition hashes.

Parallel collection: use --workers4 (Kaggle default4, CPU default1). Train/warmup/dev episodes have separate clients and budgets. Shared inference is locked only while BGE/actor/critic run; HTTP waits overlap. Parameters stay fixed until the batch barrier. Episode sampling seeds derive from run seed/phase/absolute episode index, so scheduling does not alter fixture training results. Resume may change workers. An explicit source-pair registry permits migration from published56345a4 V4 checkpoints while retaining source/config/data/model/device guards; sampling switches to episode-local generators and is logged. V3 checkpoints remain incompatible.

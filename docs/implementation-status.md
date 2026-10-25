# Implementation status

## Acceptance gates

- [ ] Pin and test Arena against the existing Isaac Sim 5.1 runtime without modifying it.
- [ ] Select direct reuse or documented adaptation based on a simulator smoke test.
- [ ] Integrate one mobile robot and one fixed 640×480 ego RGB camera.
- [ ] Validate physical move/turn/wait skills and private navigation evaluator.
- [ ] Connect gpt-6.1-sol through a restricted model transport; prove input/tool isolation.
- [ ] Execute and record the first real task, including unsuccessful attempts.
- [ ] Run constraint-randomized pilot (proposed 64 episodes).
- [ ] Expand to stable batch generation (proposed 512), report diversity and cost.

External cameras and dense H5 export are later phases. Existing batch contracts stay unchanged.

## Development policy

Development and experimental commits belong on `dev`. Only verified components selected for retention are promoted to `main`. No experiment data, credentials, third-party assets or vendor checkouts belong in Git.

## Initial server inspection

Node43 is reachable. The existing runtime reports Isaac Sim `5.1.0-rc.19+release.26219.9c81211b.gl` in its VERSION file. Existing campaign manifests report 20/20 complete and 8/40 accepted; live simulator processes and the new campaign supervisor were confirmed. GPU memory usage alone is not a reservation signal.

All new simulation processes must acquire the same existing per-GPU lock:
`/local_nvme/zhangrong/isaac-rigidtrack-20261023/locks/campaign-gpu-{gpu}.lock`.

The new NAS workspace is `/mnt/nas/zhangrong/embodied-mosaic`, separate from existing campaigns. Arena source acquisition has started there. Its compatibility has not yet been tested.

## Prototype

`prototypes/episode_harness` contains the existing provider-independent protocol prototype. It has no model or simulator transport. See its README for the unimplemented runtime isolation and image validation requirements.

### Native ego diagnostic queued

A server-only `scripts/ego_smoke.py` diagnostic loads an accepted Carter scene in a new USD layer, disables the other robot actors, attaches a single RGB camera, and applies short native wheel commands. It is a sensor/control diagnostic, not an agent episode and not a task success result.

Server output: `/mnt/nas/zhangrong/embodied-mosaic/runs/ego-smoke-001`.
Latest queued lock process: PID 695642 on node43 (revalidate before acting). It uses the shared GPU 7 lock. The source was corrected before simulation launch to the explicit slot `source_episode`, rather than inferring provenance from the copied H5 path.

Arena release/0.1.1 pins Isaac Lab commit `6acdd82a1633732d32bb575e3d792e34fdeb437e`, whose VERSION reports 2.3.0. Arena's default Docker base is Sim 5.0.0; compatibility with our 5.1 remains to be tested. Source was transferred to the NAS vendor directory. Current server driver is 580.65.06; no Arena or Sim 6.2 container was found in the local Docker image inventory.

### Ego diagnostic 002 and dependency overlay

The second native smoke run completed 90 RGB frames (640×480). Frame 19 was visually inspected: warehouse shelving, floor and wall were visible with no robot self-occlusion in that sample. Measured forward displacement between frames 15 and 59 was 0.17374 m. The wrapped yaw change during the short turn was approximately 2.98 degrees, below the roughly 9-degree command; closed-loop skill endpoint control is still required. No agent task was executed.

The first smoke attempt failed with an empty RGB annotator buffer. Explicit Replicator capture fixed that failure. Logs for both attempts remain on NAS.

Seven missing Python dependencies were installed into a project-specific `runtime/python-deps` directory using offline wheels. The server's default package mirror timed out, so it was not used further. The existing simulation package environment was not modified. Arena probe 001 is queued/running under the shared GPU 7 lock, PID 721291; inspect its result before claiming compatibility.

The user confirmed the model setting as `gpt-6.1-sol` with `low` reasoning. The config and protocol tests now assert that setting; a live restricted model transport remains unverified.

### Feedback control and restricted CLI investigation

Feedback smoke 001 completed on node43: a 0.20 m forward request moved approximately 0.1931 m; a 20-degree turn changed yaw approximately 19.03 degrees. All three diagnostic skills reached their endpoint criteria. This is not yet a collision-tested navigation episode. Private diagnostics remain in `runs/ego-feedback-001/diagnostic.json` on NAS.

Arena probe 002 imported its environment, scene and asset registry successfully after adding hidapi to the isolated dependency overlay. Ground-plane spawning failed with a None collision-prim path passed to Stage.GetPrimAtPath. Runtime compatibility is still unverified; the ground asset resolution and spawn path need inspection.

The user confirmed that only Codex login is available and requested continued investigation of restricted CLI transport. Installed CLI version: 0.140.0. Its help exposes ignore-user-config, ignore-rules, ephemeral sessions, image input and output-schema. A bubblewrap user/PID namespace smoke test succeeded locally; it used a read-only root bind solely to check availability, NOT to prove filesystem isolation.

The generated app-server schema supports explicit base instructions, ephemeral sessions and environment selection. An empty dynamicTools list does not establish that built-in tools are absent. Current upstream source registers apply_patch based on model metadata independently of the shell-tool switch. Therefore disabling shell alone is insufficient. This source inspection uses upstream main, not a verified source match for the installed binary. No isolated model call has passed acceptance yet.

Next transport gates: a minimal filesystem allowlist; no inherited project/user instructions or plugins; explicit tool inventory verification; out-of-sandbox canary rejection; a live ego-image to skill-JSON call using gpt-6.1-sol at low reasoning. Authentication must stay outside model-visible context and all credential material stays out of Git and episode logs.

References inspected: https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/spec_plan.rs and https://github.com/openai/codex/blob/main/codex-rs/core/config.schema.json.

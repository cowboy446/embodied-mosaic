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

### Offline CLI audit 009

An actual request emitted by installed CLI 0.140.0 was captured by a dummy localhost Responses provider. No live model was called; request headers and authentication were not logged. The first connection attempt was inadvertently routed through a host proxy; removing proxy variables for the localhost-only audit fixed it.

Changing model transport metadata to direct tool mode and disabled multi-agent mode removed code execution and collaboration tools. A bubblewrap allowlist mounted system runtime directories plus the temporary request directory, excluding host home, project directories and NAS. Disabling automatic skills and permission instruction blocks produced a request containing only the CLI environment context and the explicit audit prompt. This verifies the captured context boundary for this offline configuration, not the live authenticated transport.

Two tools remain registered: update_plan and view_image. Consequently strict no-tool acceptance remains open. Host authentication was deliberately not mounted during this test. Next: enforce an episode-only image surface, test outside-path rejection, and establish authenticated image/JSON transport without exposing credentials through tools.

### Observation validation and filesystem probe

The episode protocol now fully decodes PNG inputs, requires a single 640x480 RGB frame, and re-encodes only pixel data to strip nonvisual metadata. It rejects replacing an already issued observation. Eight boundary tests pass, including malformed images, dimensions/channels and metadata leakage checks. Pillow is now an explicit prototype dependency.

Offline CLI audit 010 executes path-visibility assertions inside the same bubblewrap namespace: host auth.json, the current project directory and /mnt/nas are absent. This verifies these specific filesystem exclusions; authenticated transport and complete tool removal remain unverified.

Arena diagnostic 003 was queued on node43 under the existing GPU 7 lock (PID 804957). It records the ground asset URI and loaded prim types on failure. Revalidate its process/output before interpreting the result.

### Body observations, skill profiles, and Arena asset diagnosis

The user expanded allowed observations to nonprivileged proprioception. The protocol now accepts optional encoder and body-frame IMU channels with exact field validation; global poses and arbitrary simulator dictionaries remain excluded. No sensor-source provenance claim is made until the corresponding simulator adapter is audited.

Skill definitions now live in an embodiment registry. The Carter base profile drives both public schema and action validation, with per-episode copies. Unknown/unimplemented profiles fail closed. Persistent VLA/motion-tracking lifecycle and actuator ownership requirements are documented but not implemented. Thirteen boundary tests pass.

Arena probe 003 never launched because the shell wrapper was not executable; probe 004 used bash explicitly. It revealed ground_usd_path = None/Isaac/Environments/Grid/default_environment.usd, with no loaded geometry. Isaac Lab reads /persistent/isaac/asset_root/cloud at import time; this setting was absent. Probe 005 explicitly supplies the 5.1 asset root found in the installed asset-browser configuration and is queued/running under the same GPU 7 lock (PID 828974). This is a configuration diagnosis, not proof of full Arena compatibility.

Probe 005 completed its scoped checks successfully: environment/scene/registry imports and ten Isaac Lab simulation steps. Saved evidence: evidence/arena-probe-005.json. Full Carter Scene × Robot × Task execution remains unverified.

### Authenticated CLI result and prompt-constrained pilot

Live CLI smoke 001 authenticated successfully but the backend rejected gpt-6.1-sol with model_not_found / not supported for this ChatGPT account transport. No model action was returned or executed. No fallback model was selected. The user explicitly authorized a fresh-context gpt-6.1-sol + low subagent for the first prompt-constrained closed loop while strict tool isolation remains open.

A mailbox-driven server pilot and coordinator-only SSH bridge were added. The policy sees RGB, semantic goal, skill bounds, own recent actions and wheel encoder readings. Target coordinates and poses are confined to the server's private logs/evaluation. The pilot uses a forward ray fan, not a full swept-volume collision certificate, and must not count toward batch safety acceptance. Queued on node43 with GPU 7 lock: ego-agent-001, PID 853804.

Arena probe 005 completed its reported checks but its process remained alive in shutdown for over five minutes, retaining the GPU lock. The exact diagnostic child PID 830227 was verified and sent SIGTERM; the incident is recorded on NAS. Thus successful stepping does not establish clean runtime lifecycle compatibility.

### First prompt-constrained episode completed

Episode ego-agent-001 ran on node43 GPU 7 and exited normally. A fresh-context gpt-6.1-sol low policy selected move_forward 0.3 m twice, then finish. The independent private evaluator measured 1.21455 m remaining from robot center to target and rejected task success. Both movement controllers returned reached; final settling speed was 0.000612 m/s. This is a completed closed-loop pilot with policy failure, not a successful navigation task or strict-isolation acceptance. 255 RGB frames including initial observation and a 30 fps MP4 are retained on NAS; the small preview and observation packets are copied locally under runs/policy-001. The policy agent has ended and must not be reused for another episode.

A scheduling attempt to move the waiting pilot to GPU 3 raced with the original GPU 7 start. Its precondition correctly detected an existing child, but the surrounding shell lacked fail-fast behavior and continued. The duplicate failed at exclusive output-directory creation before SimulationApp initialization. The original run remained active; its PID file was restored. Future scheduling scripts must fail closed on prerequisite checks.

Local harness.py was observed changed back to an older interface outside this edit sequence. Its contents were preserved under runs/external-edits and not overwritten. Server pilot used the previously uploaded proprioception/skill-registry version. Reconcile the local edit before deploying subsequent episodes.

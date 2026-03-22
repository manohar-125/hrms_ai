import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from app.vectordb.api_vector_store import APIVectorStore


REGISTRY_PATH = PROJECT_ROOT / "app/tools/api_registry.json"
REQUIRED_FIELDS = {"endpoint", "method"}


def _file_hash(path: Path) -> str:
	payload = path.read_bytes()
	return hashlib.sha256(payload).hexdigest()


def _validate_registry(path: Path):
	with open(path, "r") as f:
		registry = json.load(f)

	if not isinstance(registry, dict):
		raise ValueError("api_registry.json must contain a JSON object")

	for tool_name, tool_data in registry.items():
		if not isinstance(tool_data, dict):
			raise ValueError(f"Tool '{tool_name}' must be a JSON object")

		missing = REQUIRED_FIELDS - set(tool_data.keys())
		if missing:
			missing_str = ", ".join(sorted(missing))
			raise ValueError(f"Tool '{tool_name}' is missing required fields: {missing_str}")

	return registry


def run_sync():
	if not REGISTRY_PATH.exists():
		raise FileNotFoundError(f"Registry file not found: {REGISTRY_PATH}")

	_validate_registry(REGISTRY_PATH)

	store = APIVectorStore()
	stats = store.sync_tools(registry_path=str(REGISTRY_PATH))

	print(
		"Registry sync complete | "
		f"upserted={stats['upserted']} "
		f"deleted={stats['deleted']} "
		f"total_registry={stats['total_registry']}"
	)


def main():
	parser = argparse.ArgumentParser(
		description="Sync app/tools/api_registry.json to vector DB (upsert + stale delete)."
	)
	parser.add_argument(
		"--watch",
		action="store_true",
		help="Watch api_registry.json and auto-sync on every file change.",
	)
	parser.add_argument(
		"--interval",
		type=float,
		default=2.0,
		help="Polling interval in seconds when --watch is enabled.",
	)
	args = parser.parse_args()

	run_sync()

	if not args.watch:
		return

	print("Watch mode enabled for app/tools/api_registry.json")
	last_hash = _file_hash(REGISTRY_PATH)

	while True:
		try:
			time.sleep(args.interval)

			current_hash = _file_hash(REGISTRY_PATH)
			if current_hash == last_hash:
				continue

			print("Detected registry change. Re-syncing...")
			run_sync()
			last_hash = current_hash

		except KeyboardInterrupt:
			print("Watch stopped by user")
			break
		except Exception as exc:
			print(f"Sync error: {exc}")


if __name__ == "__main__":
	main()
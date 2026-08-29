# Power Core

Runtime infrastructure for Power Trader applications.

## Overview

Power Core provides the runtime components that applications need:
- **Application** - Lifecycle management (startup/shutdown)  
- **DIContainer** - Dependency injection infrastructure
- **PluginRegistry** - Strategy plugin discovery and loading

## Relationship to Other Packages

```
power-framework (protocols) → power-core (runtime) → applications (business logic)
```

- **power-framework**: Defines interfaces (what)
- **power-core**: Provides infrastructure (how)
- **applications**: Implement business logic (specific use cases)

## Installation

```bash
uv pip install -e packages/power-core
```

## Usage

### Creating an Application

```python
from power_core import Application, DIContainer, PluginRegistry
from power_framework.protocols import IMarketDataProvider

# Create DI container
class MyAppContainer(DIContainer):
    # Register your dependencies
    pass

# Create application
container = MyAppContainer()
app = Application(container)

# Register lifecycle hooks
app.on_startup(async_startup_function)
app.on_shutdown(async_shutdown_function)

# Run
await app.run()
```

### Plugin Discovery

```python
from power_core import PluginRegistry

registry = PluginRegistry()

# Discover strategies from installed packages
registry.discover_strategies()

# Get all strategies
strategies = registry.get_all_strategies()

# Initialize them
await registry.initialize_all()
```

## Features

✅ **Async lifecycle management**
✅ **Signal handling** (SIGINT, SIGTERM)
✅ **Graceful shutdown**
✅ **Automatic plugin discovery**
✅ **Type-safe DI** with that-depends

## License

MIT

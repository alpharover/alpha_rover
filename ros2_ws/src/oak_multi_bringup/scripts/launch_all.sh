#!/bin/bash

# OAK Multi Sensor Launch Script
# Launches all sensors in proper sequence with error handling

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
WORKSPACE_DIR="$HOME/ros2_ws"
FOXGLOVE_ENABLED=false
WAIT_TIME=3
MAP_ENABLED=false
NVBLOX_PID=""
LIDAR_MODE="front"  # front|rear|both
LIDAR_ONLY=false     # Skip cameras; map with LiDAR only
HEALTH_ENABLED=false
NO_CLEANUP=false     # If true, skip cleanup and enable duplicate-guards

# Simple helpers for duplicate guards
node_exists() {
    # Usage: node_exists "/node_name"
    timeout 2 ros2 node list 2>/dev/null | grep -q "^$1$"
}

topic_exists() {
    # Usage: topic_exists "/topic_name"
    timeout 2 ros2 topic list 2>/dev/null | grep -q "^$1$"
}

proc_exists() {
    # Usage: proc_exists "pattern"
    pgrep -f "$1" >/dev/null 2>&1
}

wait_for_pgone() {
    # Usage: wait_for_pgone "pattern" [timeout_sec] [exclude_pid]
    local pattern="$1"; shift
    local timeout="${1:-5}"; shift || true
    local exclude_pid="${1:-}"
    local elapsed=0
    while true; do
        # collect pids matching pattern, excluding optional PID
        local pids
        pids=$(pgrep -f "$pattern" 2>/dev/null || true)
        local remain=()
        if [ -n "$pids" ]; then
            for pid in $pids; do
                if [ -z "$exclude_pid" ] || [ "$pid" != "$exclude_pid" ]; then
                    remain+=("$pid")
                fi
            done
        fi
        if [ ${#remain[@]} -eq 0 ]; then
            break
        fi
        if [ "$elapsed" -ge "$timeout" ]; then
            # force kill only remaining PIDs (do not kill our own shell)
            kill -9 "${remain[@]}" 2>/dev/null || true
            break
        fi
        sleep 0.5
        elapsed=$((elapsed+1))
    done
}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if ROS is sourced
check_ros_env() {
    if [ -z "$ROS_DISTRO" ]; then
        print_error "ROS environment not sourced. Please run:"
        echo "source /opt/ros/humble/setup.bash"
        exit 1
    fi
}

# Function to build and source workspace
setup_workspace() {
    print_status "Setting up workspace..."
    cd "$WORKSPACE_DIR"

    # Ensure rslidar_sdk has its vendor driver present (handles moved workspace or private submodule)
    ensure_rslidar_vendor() {
        local sdk_dir="$WORKSPACE_DIR/src/rslidar_sdk"
        local rsdrv_dir="$sdk_dir/src/rs_driver"
        if [ -d "$sdk_dir" ]; then
            if [ ! -f "$rsdrv_dir/CMakeLists.txt" ]; then
                print_warning "rs_driver not found in rslidar_sdk; attempting to initialize submodule"
                if command -v git >/dev/null 2>&1; then
                    # Try nested submodule init (may require GitHub access)
                    git -C "$sdk_dir" submodule update --init --recursive src/rs_driver >/dev/null 2>&1 || true
                fi
            fi
            if [ ! -f "$rsdrv_dir/CMakeLists.txt" ]; then
                # Fallback to vendoring from legacy backup snapshot (pre-move copy)
                local legacy_dir="$HOME/alpha_rover/legacy/src_pre_20250825/rslidar_sdk/src/rs_driver"
                if [ -f "$legacy_dir/CMakeLists.txt" ]; then
                    print_status "Restoring rs_driver from legacy backup snapshot"
                    rm -rf "$rsdrv_dir"
                    mkdir -p "$sdk_dir/src"
                    cp -a "$legacy_dir" "$rsdrv_dir"
                    print_success "rs_driver restored for local build"
                else
                    print_warning "Legacy rs_driver not found; rslidar_sdk build may fail"
                fi
            fi
        fi
    }

    ensure_rslidar_vendor

    # Build required packages. Always include LiDAR drivers so they are available to launch.
    # Include nvblox bringup when mapping is enabled.
    if [ "$MAP_ENABLED" = true ]; then
        SELECT_PACKAGES="oak_multi_bringup oak_nvblox_bringup rslidar_sdk rslidar_msg lidar_tools lidar_tools_cpp"
    else
        SELECT_PACKAGES="oak_multi_bringup rslidar_sdk rslidar_msg"
    fi

    if ! colcon build --packages-select $SELECT_PACKAGES --symlink-install; then
        print_error "Failed to build oak_multi_bringup package"
        exit 1
    fi
    
    source "$WORKSPACE_DIR/install/setup.bash"
    print_success "Workspace built and sourced"
}

# Function to kill existing processes
cleanup_existing() {
    print_status "Cleaning up existing processes..."
    # Terminate any other running launchers of this script to prevent hangs
    if command -v pgrep >/dev/null 2>&1; then
        for pid in $(pgrep -f "oak_multi_bringup/scripts/launch_all.sh" || true); do
            if [ "$pid" != "$$" ]; then
                kill "$pid" 2>/dev/null || true
            fi
        done
        wait_for_pgone "oak_multi_bringup/scripts/launch_all.sh" 8 "$$"
    fi
    pkill -f 'ros2 launch .*oak_multi_bringup' || true
    pkill -f 'component_container' || true
    pkill -f 'foxglove_bridge' || true
    pkill -f 'ros2 launch .*oak_nvblox_bringup' || true
    pkill -f 'nvblox_node' || true
    pkill -f 'pointcloud_merge.py' || true
    pkill -f 'rslidar_sdk' || true
    pkill -f 'rslidar_sdk_node' || true
    pkill -f 'dual_airy_start' || true
    pkill -f 'lidar_tools.pc_repack' || true
    pkill -f 'pc_repack' || true
    pkill -f 'pc_reorder' || true
    pkill -f 'wait_for_cloud' || true
    pkill -f 'wait_for_topic' || true
    pkill -f 'robot_state_publisher' || true
    pkill -f 'probe_pc' || true
    pkill -f 'probe_raw' || true
    pkill -f 'static_transform_publisher' || true
    # More aggressive cleanup for stubborn processes
    killall -9 rslidar_sdk_node 2>/dev/null || true
    pkill -9 -f 'lidar_tools.pc_repack' 2>/dev/null || true
    pkill -9 -f 'pc_reorder' 2>/dev/null || true
    pkill -9 -f 'wait_for_cloud' 2>/dev/null || true
    pkill -9 -f 'wait_for_topic' 2>/dev/null || true
    pkill -9 -f 'robot_state_publisher' 2>/dev/null || true
    pkill -9 -f 'static_transform_publisher' 2>/dev/null || true
    # Wait for key processes to fully terminate to avoid race conditions
    wait_for_pgone 'foxglove_bridge' 8
    wait_for_pgone 'nvblox_node' 6
    wait_for_pgone 'rslidar_sdk_node' 6
    wait_for_pgone 'lidar_tools.pc_repack' 4
    wait_for_pgone 'pc_reorder' 4
    wait_for_pgone 'robot_state_publisher' 4
    wait_for_pgone 'static_transform_publisher' 4
    # Ensure Foxglove port is free
    local port_wait=0
    while ss -lnt 2>/dev/null | grep -q "LISTEN .*:8765" && [ $port_wait -lt 10 ]; do
        sleep 0.5
        port_wait=$((port_wait+1))
    done
    # Reset ROS 2 daemon to drop stale graph info
    if command -v ros2 >/dev/null 2>&1; then
        ros2 daemon stop >/dev/null 2>&1 || true
        sleep 1
        ros2 daemon start >/dev/null 2>&1 || true
        sleep 1
    fi
    # Clear any stale PID/lock files
    rm -f /tmp/oak_multi_bringup.launch.pid 2>/dev/null || true
    rm -f /tmp/oak_multi_bringup.launch.lock 2>/dev/null || true
    # Put LiDAR hardware into Standby as part of cleanup
    if [ -x "$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py" ]; then
        "$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py" standby >/dev/null 2>&1 || true
    fi
    print_success "Cleanup completed"
}

# Function to launch TF
launch_tf() {
    print_status "Launching TF (robot_state_publisher)..."
    # Duplicate guard (only in no-cleanup mode)
    if [ "$NO_CLEANUP" = true ]; then
        if node_exists "/robot_state_publisher" || proc_exists "robot_state_publisher"; then
            print_warning "TF already running; skipping duplicate launch"
            return 0
        fi
    fi
    ros2 launch oak_multi_bringup robot_state.launch.py &
    TF_PID=$!
    sleep $WAIT_TIME
    
    # Check if TF is publishing
    if ! timeout 5 ros2 topic echo --once /tf_static > /dev/null 2>&1; then
        print_error "TF not publishing. Check robot_state.launch.py"
        exit 1
    fi
    print_success "TF launched successfully (PID: $TF_PID)"
}

# Function to launch OAK cameras
launch_cameras() {
    if [ "$LIDAR_ONLY" = true ]; then
        print_status "LiDAR-only mode: skipping camera launch"
        return 0
    fi
    print_status "Launching OAK-D Pro camera..."
    if [ "$NO_CLEANUP" = true ]; then
        # Duplicate guard for Pro: skip if topics already exist
        if topic_exists "/oak_d_pro/points" || topic_exists "/oak_d_pro/camera/stereo/image_raw" || proc_exists "oak_pro.launch.py"; then
            print_warning "OAK-D Pro already running; skipping"
        else
            ros2 launch oak_multi_bringup oak_pro.launch.py &
            PRO_PID=$!
            sleep $WAIT_TIME
        fi
    else
        ros2 launch oak_multi_bringup oak_pro.launch.py &
        PRO_PID=$!
        sleep $WAIT_TIME
    fi
    
    print_status "Launching OAK-D SR camera..."
    if [ "$NO_CLEANUP" = true ]; then
        # Duplicate guard for SR: skip if topics already exist
        if topic_exists "/oak_d_sr/points" || topic_exists "/oak_d_sr/camera/stereo/image_raw" || proc_exists "oak_sr.launch.py"; then
            print_warning "OAK-D SR already running; skipping"
        else
            ros2 launch oak_multi_bringup oak_sr.launch.py &
            SR_PID=$!
            sleep $WAIT_TIME
        fi
    else
        ros2 launch oak_multi_bringup oak_sr.launch.py &
        SR_PID=$!
        sleep $WAIT_TIME
    fi
    
    # Verify cameras are publishing
    if ! timeout 10 ros2 topic list | grep -q "/oak_d_pro/points"; then
        print_warning "OAK-D Pro may not be publishing correctly"
    else
        print_success "OAK-D Pro launched (PID: $PRO_PID)"
    fi
    
    if ! timeout 10 ros2 topic list | grep -q "/oak_d_sr/points"; then
        print_warning "OAK-D SR may not be publishing correctly"
    else
        print_success "OAK-D SR launched (PID: $SR_PID)"
    fi
}

# Function to launch AIRY LiDARs
launch_lidars() {
    print_status "Launching AIRY LiDARs..."
    # Ensure LiDAR hardware is in RUN mode before starting driver
    if [ -x "$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py" ]; then
        if [ "$LIDAR_ONLY" = true ]; then
            # Respect selected lidar in LiDAR-only mode
            "$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py" run --lidar "$LIDAR_MODE" >/dev/null 2>&1 || print_warning "Failed to set selected LiDAR to RUN; continuing"
        else
            "$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py" run >/dev/null 2>&1 || print_warning "Failed to set LiDARs to RUN; continuing"
        fi
        sleep 2
    fi
    if ros2 pkg list | grep -q rslidar_sdk; then
        if [ "$NO_CLEANUP" = true ]; then
            # Duplicate guard: skip if driver already running
            if node_exists "/rslidar_sdk_node" || proc_exists "rslidar_sdk_node" || proc_exists "dual_airy_start"; then
                print_warning "rslidar_sdk already running; skipping LiDAR launch"
                return 0
            fi
        fi
        if [ "$LIDAR_ONLY" = true ] && [ "$LIDAR_MODE" != "both" ]; then
            # Launch only the selected LiDAR driver directly with its config
            local prefix
            prefix=$(ros2 pkg prefix rslidar_sdk 2>/dev/null || echo "")
            if [ -z "$prefix" ]; then
                print_error "Failed to resolve rslidar_sdk prefix"
                exit 1
            fi
            local cfg
            if [ "$LIDAR_MODE" = "rear" ]; then
                cfg="$prefix/share/rslidar_sdk/config/config_airy_201.yaml"
            else
                cfg="$prefix/share/rslidar_sdk/config/config_airy_200.yaml"
            fi
            print_status "Starting rslidar_sdk_node with config: $cfg"
            ros2 run rslidar_sdk rslidar_sdk_node --ros-args -p config_path:="$cfg" &
            LIDAR_PID=$!
        else
            # Default dual launch
            ros2 launch rslidar_sdk dual_airy_start.py &
            LIDAR_PID=$!
        fi
        sleep $WAIT_TIME
        print_success "AIRY LiDARs launched (PID: $LIDAR_PID)"
    else
        print_warning "rslidar_sdk package not found. Skipping LiDARs."
    fi
}

# Function to launch Foxglove bridge
launch_foxglove() {
    if [ "$FOXGLOVE_ENABLED" = true ]; then
        if [ "$NO_CLEANUP" = true ]; then
            # In no-cleanup mode, do not start another foxglove if one is running
            if node_exists "/foxglove_bridge" || pgrep -x foxglove_bridge >/dev/null 2>&1; then
                print_warning "foxglove_bridge already running; skipping duplicate launch"
                print_status "Foxglove: ws://$(hostname -I | awk '{print $1}'):8765"
                return 0
            fi
            # If port 8765 already in use, assume an existing bridge and skip launching to avoid crash
            if ss -lnt 2>/dev/null | grep -q "LISTEN .*:8765"; then
                print_warning "Foxglove port 8765 already in use; reusing existing bridge"
            else
                print_status "Launching Foxglove bridge (direct run)..."
                ros2 run foxglove_bridge foxglove_bridge --ros-args \
                    --params-file "$HOME/ros2_ws/src/oak_multi_bringup/config/foxglove_qos.yaml" \
                    -p port:=8765 &
                FOXGLOVE_PID=$!
                sleep $WAIT_TIME
                print_success "Foxglove bridge launched (PID: $FOXGLOVE_PID)"
            fi
        else
            # After cleanup we ensure single instance by waiting for port to free
            # Extra safety: terminate any lingering foxglove process before starting
            if pgrep -x foxglove_bridge >/dev/null 2>&1; then
                pkill -x foxglove_bridge || true
                wait_for_pgone 'foxglove_bridge' 8
            fi
            local tries=0
            while ss -lnt 2>/dev/null | grep -q "LISTEN .*:8765" && [ $tries -lt 8 ]; do
                sleep 0.5
                tries=$((tries+1))
            done
            print_status "Launching Foxglove bridge (direct run)..."
            ros2 run foxglove_bridge foxglove_bridge --ros-args \
                --params-file "$HOME/ros2_ws/src/oak_multi_bringup/config/foxglove_qos.yaml" \
                -p port:=8765 &
            FOXGLOVE_PID=$!
            sleep $WAIT_TIME
            print_success "Foxglove bridge launched (PID: $FOXGLOVE_PID)"
        fi
        print_status "Foxglove: ws://$(hostname -I | awk '{print $1}'):8765"
    fi
}

# Function to launch health monitors (Jetson + OAK temps)
launch_health() {
    if [ "$HEALTH_ENABLED" = true ]; then
        print_status "Launching health monitors (Jetson thermals + OAK temps)..."
        if ros2 pkg list | grep -q sensor_health_monitor; then
            ros2 launch sensor_health_monitor thermals.launch.py &
            HEALTH_JETSON_PID=$!
        else
            print_warning "sensor_health_monitor package not found."
        fi
        if ros2 pkg list | grep -q oak_temp_bridge; then
            ros2 launch oak_temp_bridge oak_temp_bridge.launch.py &
            HEALTH_OAK_PID=$!
        else
            print_warning "oak_temp_bridge package not found."
        fi
        sleep $WAIT_TIME
        print_success "Health monitors launched"
    fi
}

# Function to launch nvblox (depth-only)
launch_nvblox() {
    if [ "$MAP_ENABLED" != true ]; then
        return 0
    fi
    # Deterministic, no-guard NVBlox startup
    local extra_args
    extra_args=${NVBLOX_ARGS:-"voxel_size:=0.05 lidar_integrate_hz:=10.0 streamer_mbps:=50.0 max_queue_len:=3"}
    if [ "$LIDAR_ONLY" = true ]; then
        local lidar_topic
        if [ "$LIDAR_MODE" = "rear" ]; then
            lidar_topic="/airy_201/rslidar_points"
        elif [ "$LIDAR_MODE" = "front" ]; then
            lidar_topic="/airy_200/rslidar_points"
        else
            print_warning "LiDAR-only mode does not support 'both'; defaulting to rear"
            lidar_topic="/airy_201/rslidar_points"
        fi
        print_status "LiDAR stabilize delay: 10s before NVBlox start..."
        sleep 10
        pkill -f nvblox_node 2>/dev/null || true
        wait_for_pgone 'nvblox_node' 6
        print_status "Launching nvblox (LiDAR-only; repack enabled; topic=$lidar_topic)..."
        ros2 launch oak_nvblox_bringup nvblox_lidar_only.launch.py \
            lidar_points_topic:=$lidar_topic \
            use_repack:=true use_cpp_repack:=true \
            repack_throttle_n:=1 repack_qos_depth:=1 \
            repack_angle_csv:="$HOME/alpha_rover/channel_distance_table.csv" \
            $extra_args > "$WORKSPACE_DIR/log_nvblox_map.txt" 2>&1 &
        NVBLOX_PID=$!
        sleep $WAIT_TIME
        print_success "nvblox launched (PID: $NVBLOX_PID)"
    else
        # Cameras + LiDAR mapping
        local lidar_param="/airy_200/rslidar_points"
        if [ "$LIDAR_MODE" = "rear" ]; then
            lidar_param="/airy_201/rslidar_points"
        fi
        pkill -f nvblox_node 2>/dev/null || true
        wait_for_pgone 'nvblox_node' 6
        print_status "Launching nvblox (dual cams + LiDAR, topic=$lidar_param)..."
        ros2 launch oak_nvblox_bringup nvblox_dual_cams_with_lidar.launch.py lidar_points_topic:=$lidar_param > "$WORKSPACE_DIR/log_nvblox_map.txt" 2>&1 &
        NVBLOX_PID=$!
        sleep $WAIT_TIME
        print_success "nvblox launched (PID: $NVBLOX_PID)"
    fi
}

# Function to monitor processes
monitor_processes() {
    print_success "All sensors launched successfully!"
    echo
    print_status "Active processes:"
    [ ! -z "$TF_PID" ] && echo "  - TF Publisher: $TF_PID"
    [ ! -z "$PRO_PID" ] && echo "  - OAK-D Pro: $PRO_PID"
    [ ! -z "$SR_PID" ] && echo "  - OAK-D SR: $SR_PID" 
    [ ! -z "$LIDAR_PID" ] && echo "  - AIRY LiDARs: $LIDAR_PID"
    [ ! -z "$FOXGLOVE_PID" ] && echo "  - Foxglove: $FOXGLOVE_PID"
    [ ! -z "$NVBLOX_PID" ] && echo "  - nvblox: $NVBLOX_PID"
    echo
    print_status "Press Ctrl+C to stop all processes"
    
    # Wait for interrupt
    trap cleanup_and_exit INT
    wait
}

# Cleanup function
cleanup_and_exit() {
    print_status "Shutting down all processes..."
    [ ! -z "$NVBLOX_PID" ] && kill $NVBLOX_PID 2>/dev/null || true
    [ ! -z "$FOXGLOVE_PID" ] && kill $FOXGLOVE_PID 2>/dev/null || true
    [ ! -z "$LIDAR_PID" ] && kill $LIDAR_PID 2>/dev/null || true
    [ ! -z "$SR_PID" ] && kill $SR_PID 2>/dev/null || true
    [ ! -z "$PRO_PID" ] && kill $PRO_PID 2>/dev/null || true
    [ ! -z "$TF_PID" ] && kill $TF_PID 2>/dev/null || true

    # Kill all rslidar processes more aggressively
    pkill -f 'rslidar_sdk_node' || true
    pkill -f 'nvblox_node' || true
    pkill -f 'pointcloud_merge.py' || true
    pkill -f 'lidar_tools.pc_repack' || true
    pkill -f 'static_transform_publisher' || true
    pkill -f 'wait_for_cloud' || true
    pkill -f 'wait_for_topic' || true
    sleep 1
    killall -9 rslidar_sdk_node 2>/dev/null || true
    pkill -9 -f 'nvblox_node' 2>/dev/null || true
    pkill -9 -f 'lidar_tools.pc_repack' 2>/dev/null || true
    pkill -9 -f 'static_transform_publisher' 2>/dev/null || true
    pkill -9 -f 'wait_for_cloud' 2>/dev/null || true
    pkill -9 -f 'wait_for_topic' 2>/dev/null || true
    
    sleep 2
    # Put LiDAR hardware into Standby to reduce heat
    if [ -x "$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py" ]; then
        "$HOME/ros2_ws/src/oak_multi_bringup/scripts/oak_lidar.py" standby >/dev/null 2>&1 || true
    fi
    print_success "All processes stopped"
    exit 0
}

# Help function
show_help() {
    echo "OAK Multi Sensor Launch Script"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -f, --foxglove    Enable Foxglove bridge"
    echo "  -H, --health      Enable health monitors (temps)"
    echo "  -c, --cleanup     Clean up existing processes only"
    echo "      --no-cleanup  Skip cleanup and use duplicate guards instead"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                Launch all sensors without Foxglove"
    echo "  $0 -f             Launch all sensors with Foxglove"
    echo "  $0 --cleanup      Clean up existing processes"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--foxglove)
            FOXGLOVE_ENABLED=true
            shift
            ;;
        -m|--map)
            MAP_ENABLED=true
            FOXGLOVE_ENABLED=true
            shift
            ;;
        --lidar-only)
            LIDAR_ONLY=true
            MAP_ENABLED=true
            FOXGLOVE_ENABLED=true
            shift
            ;;
        -H|--health)
            HEALTH_ENABLED=true
            shift
            ;;
        --lidar)
            LIDAR_MODE="$2"
            shift 2
            ;;
        -c|--cleanup)
            check_ros_env
            cleanup_existing
            exit 0
            ;;
        --no-cleanup)
            NO_CLEANUP=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Starting OAK Multi Sensor Launch..."
    # Soft singleton via PID file (avoids stuck locks inherited by children)
    local PID_FILE="/tmp/oak_multi_bringup.launch.pid"
    if [ -f "$PID_FILE" ]; then
        local oldpid; oldpid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$oldpid" ] && [ "$oldpid" != "$$" ] && ps -p "$oldpid" >/dev/null 2>&1; then
            print_warning "Another OAK launcher detected (pid=$oldpid); requesting it to stop..."
            kill "$oldpid" 2>/dev/null || true
            # Also kill any other matching launchers
            if command -v pgrep >/dev/null 2>&1; then
                for pid in $(pgrep -f "oak_multi_bringup/scripts/launch_all.sh" || true); do
                    if [ "$pid" != "$$" ] && [ "$pid" != "$oldpid" ]; then
                        kill "$pid" 2>/dev/null || true
                    fi
                done
            fi
            wait_for_pgone "oak_multi_bringup/scripts/launch_all.sh" 10 "$$"
        fi
        # Stale pid file — remove
        rm -f "$PID_FILE" 2>/dev/null || true
    fi
    echo "$$" > "$PID_FILE" 2>/dev/null || true
    trap 'rm -f /tmp/oak_multi_bringup.launch.pid 2>/dev/null || true' EXIT
    
    check_ros_env
    if [ "$NO_CLEANUP" = true ]; then
        print_warning "Skipping cleanup as requested; enabling duplicate guards"
    else
        cleanup_existing
    fi
    setup_workspace
    launch_tf
    launch_cameras
    launch_lidars
    # Start NVBlox before Foxglove to avoid reconnection races
    launch_nvblox
    launch_foxglove
    launch_health
    # Monitoring (PID file remains; new invocations will signal/replace)
    monitor_processes
}

# Run main function
main

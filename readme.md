要使用 TARE Planner 在 Matterport3D 数据集上运行，请按照以下步骤操作：

---

### **1. 设置 Autonomous Exploration Development Environment**
#### 克隆仓库并切换分支：
1. 下载并设置 `autonomous_exploration_development_environment` 仓库的默认设置：
   ```bash
   git clone https://github.com/<your-repository>/autonomous_exploration_development_environment.git
   cd autonomous_exploration_development_environment
   ```

2. 切换到 `distribution-matterport` 分支（根据你的 ROS 版本将 `distribution` 替换为 `melodic` 或 `noetic`）：
   ```bash
   git checkout noetic-matterport
   catkin_make
   ```

---

### **2. 准备 Matterport3D 环境模型**
#### 下载并预处理模型：
1. 安装 **MeshLab**（版本 v2020.12 或更高）：
   - 下载链接：[MeshLab](https://www.meshlab.net)
   
2. 前往 [Matterport3D](https://niessner.github.io/Matterport) 网站，签署使用协议，并使用提供的 `download_mp.py` 脚本下载环境模型：
   ```bash
   python2 download_mp.py --task habitat -o data_download_dir
   ```
3. 解压下载的 `matterport_mesh.zip` 文件。以环境 ID `17DRP5sb8fy` 为例：
   - 解压并加载 `.obj` 文件到 **MeshLab**，查看彩色网格。

4. 将网格文件导出为 **DAE 格式**，保存为 `matterport.dae`，并与 `.mtl`、`.obj`、`.jpg` 文件一起复制到以下目录：
   ```plaintext
   src/vehicle_simulator/mesh/matterport/meshes
   ```

#### 处理分段文件：
1. 解压 `house_segmentations.zip` 文件：
   - 将 `.house` 文件重命名为 `matterport.house`，并复制到：
     ```plaintext
     src/vehicle_simulator/mesh/matterport/segmentations
     ```
   - 将 `.ply` 文件重命名为 `pointcloud.ply`，并复制到：
     ```plaintext
     src/vehicle_simulator/mesh/matterport/preview
     ```

---

### **3. 启动 Matterport3D 系统**
#### 启动 ROS 环境和仿真系统：
1. 在终端中，进入工作区并启动仿真系统：
   ```bash
   source devel/setup.sh
   roslaunch vehicle_simulator system_matterport.launch
   ```

#### 启动 TARE Planner：
2. 在第二个终端中，进入 `autonomous_exploration_development_environment` 工作区并启动 TARE Planner：
   ```bash
   source devel/setup.sh
   roslaunch tare_planner explore_matterport.launch
   ```

---

### **4. 验证与可视化**
1. 打开 RVIZ：
   - 在 RVIZ 中，你应该能够看到以下内容：
     - 左侧：RGB 图像
     - 中间：深度图像
     - 右侧：点云
     - 底部：整体地图、探索区域、车辆轨迹

2. 在 RVIZ 中启用以下选项以显示分割和地图信息：
   - `Panels -> Displays`，选择：
     - **DepthCloud**（点云）
     - **RegionMarkers** 和 **ObjectMarkers**（分割结果）

---

### **5. 使用导航边界与起始位置**
#### 配置起始位置和边界：
1. 安装 **CloudCompare**（v2.11.1 或更高版本）：
   - 下载链接：[CloudCompare](https://www.danielgm.net/cc)

2. 使用 `Tools -> Point picking` 来选择起始位置，并编辑以下参数：
   - 打开并编辑：
     ```plaintext
     src/vehicle_simulator/launch/system_matterport.launch
     ```
   - 设置：
     ```yaml
     vehicleX: <你的X坐标>
     vehicleY: <你的Y坐标>
     terrainZ: <你的Z坐标>
     ```

3. 使用 `Tools -> Point list picking` 设置导航边界，将结果保存为 `boundary_matterport.ply`，并放置到以下目录：
   ```plaintext
   src/waypoint_example/data
   ```

---

### **6. 离线处理（可选，Habitat 集成）**
#### 安装 Habitat：
1. 安装 Anaconda：
   - 下载链接：[Anaconda](https://www.anaconda.com)
   
2. 创建 Habitat 环境并安装：
   ```bash
   conda create -n habitat python=3.8 cmake=3.14.0
   conda activate habitat
   conda install habitat-sim=0.2.1 -c conda-forge -c aihabitat
   ```

3. 使用 `Matterport3D` 的 `--task habitat` 标志下载 Habitat 格式的模型：
   ```bash
   python2 download_mp.py --task habitat -o data_download_dir
   ```

4. 克隆 Habitat 仓库并测试：
   ```bash
   git clone --branch stable https://github.com/facebookresearch/habitat-sim.git
   cd habitat-sim/examples
   python3 example.py --scene extracted_mp3d_habitat_dir/environment_id.glb \
       --semantic_sensor --depth_sensor --save_png
   ```

---

### **7. 测试 Waypoint 示例**
1. 运行导航边界和路径规划的示例：
   ```bash
   roslaunch waypoint_example waypoint_example_matterport.launch
   ```

---

保存点云：rosrun pcl_ros pointcloud_to_pcd input:=/explored_areas _prefix:=pointcloud


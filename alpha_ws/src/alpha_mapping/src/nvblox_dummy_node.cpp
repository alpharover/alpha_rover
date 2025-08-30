// Minimal placeholder NVBlox provider node that subscribes to front/rear clouds
// and logs basic info. Replace with real provider integration.

#include <memory>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>

using std::placeholders::_1;

class NvbloxDummyNode : public rclcpp::Node {
public:
  NvbloxDummyNode() : rclcpp::Node("alpha_mapping_nvblox") {
    sub_front_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
        "/alpha/lidar/front/points", 10,
        std::bind(&NvbloxDummyNode::onCloudFront, this, _1));
    sub_rear_ = this->create_subscription<sensor_msgs::msg::PointCloud2>(
        "/alpha/lidar/rear/points", 10,
        std::bind(&NvbloxDummyNode::onCloudRear, this, _1));
    RCLCPP_INFO(this->get_logger(), "Nvblox dummy node started (waiting for clouds)");
  }

private:
  void onCloudFront(const sensor_msgs::msg::PointCloud2::SharedPtr msg) {
    RCLCPP_DEBUG(this->get_logger(), "front cloud %ux%u step=%u", msg->height, msg->width, msg->point_step);
    last_front_ = msg->header.stamp;
  }
  void onCloudRear(const sensor_msgs::msg::PointCloud2::SharedPtr msg) {
    RCLCPP_DEBUG(this->get_logger(), "rear cloud %ux%u step=%u", msg->height, msg->width, msg->point_step);
    last_rear_ = msg->header.stamp;
  }

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_front_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_rear_;
  rclcpp::Time last_front_;
  rclcpp::Time last_rear_;
};

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<NvbloxDummyNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}


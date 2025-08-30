// alpha_mapping/include/alpha_mapping/provider_interface.hpp
#pragma once

#include <memory>
#include <string>

// Forward declarations to avoid heavy deps in the interface header.
namespace rclcpp { class Node; class Time; }
namespace sensor_msgs { namespace msg { class PointCloud2; } }

namespace alpha_mapping {

class IMappingProvider {
public:
  virtual ~IMappingProvider() = default;
  virtual bool configure(rclcpp::Node* node) = 0;
  virtual void integrateCloud(const std::shared_ptr<sensor_msgs::msg::PointCloud2>& cloud,
                              const std::string& frame_id,
                              const rclcpp::Time& stamp) = 0;
  // Placeholder API for future layers
  virtual void reset() = 0;
};

} // namespace alpha_mapping


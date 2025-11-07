// --- START OF FILE config/config.go ---
package config

import (
	"encoding/json"
	"fmt"
	"os"
)

type Config struct {
	AWSProfiles []AWSProfileConfig `json:"aws_profiles"`
}

type AWSProfileConfig struct {
	ProfileName string `json:"profileName"`
	RegionName  string `json:"region_name"`
}

type WAFConfig struct {
	WAFLogSources []WAFLogSourceConfig `json:"waf_log_sources"`
}

// Ensure that WAFLogSourceConfig is defined.
// You may add additional fields as needed.
type WAFLogSourceConfig struct {
	ProfileName     string `json:"profileName"`
	Region          string `json:"region"`
	WebACLName      string `json:"webACLName"`
	WebACLID        string `json:"webACLID"`
	LogSourceName   string `json:"logSourceName"`
	LogSourceType   string `json:"logSourceType"`
	DestinationARN  string `json:"destinationARN"`
	S3BucketName    string `json:"s3BucketName"`
	CWLogsGroupName string `json:"cwLogsGroupName"`
	Scope           string `json:"scope"` // Add this field
}

func LoadConfig(filename string) (*Config, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, fmt.Errorf("error reading config file: %w", err)
	}

	var config Config
	if err := json.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("error parsing config file: %w", err)
	}
	return &config, nil
}

func LoadWAFConfig(filename string) (*WAFConfig, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil // waf-config.json is optional
		}
		return nil, fmt.Errorf("error reading waf-config file: %w", err)
	}

	var wafConfig WAFConfig
	if err := json.Unmarshal(data, &wafConfig); err != nil {
		return nil, fmt.Errorf("error parsing waf-config file: %w", err)
	}
	return &wafConfig, nil
}

func FindWAFLogSource(wafCfg *WAFConfig, profileName, logSourceName string) (*WAFLogSourceConfig, error) {
	if wafCfg == nil || wafCfg.WAFLogSources == nil {
		return nil, fmt.Errorf("waf-config.json not loaded or empty")
	}
	for _, source := range wafCfg.WAFLogSources {
		if source.ProfileName == profileName && source.LogSourceName == logSourceName {
			return &source, nil
		}
	}
	return nil, fmt.Errorf("WAF Log Source '%s' not found for profile '%s' in waf-config.json", logSourceName, profileName)
}

// --- END OF FILE config/config.go ---

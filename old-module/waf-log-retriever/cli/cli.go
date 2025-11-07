// --- START OF FILE cli/cli.go ---
package cli

import (
    "bufio"
    "fmt"
    "os"
    "strconv"
    "strings"

    "waf-log-retriever/aws"
)

// PromptUserForWAFSourceSelection presents discovered sources to the user and gets their selection
func PromptUserForWAFSourceSelection(sources []*aws.WAFLogSource) (*aws.WAFLogSource, error) {
    reader := bufio.NewReader(os.Stdin)

    fmt.Println("\nDiscovered WAF Log Sources:")
    for i, source := range sources {
        fmt.Printf("%d. Web ACL: %s, Scope: %s, Region: %s, Log Source: %s, Destination: %s\n",
        i+1, source.WebACLName, source.Scope, source.Region, source.LogSourceType, source.DestinationARN)
    }

    for {
        fmt.Print("\nSelect a WAF Log Source (enter number): ")
        input, _ := reader.ReadString('\n')
        input = strings.TrimSpace(input)

        selectedIndex, err := strconv.Atoi(input)
        if err != nil || selectedIndex < 1 || selectedIndex > len(sources) {
            fmt.Println("Invalid selection. Please enter a number from the list.")
            continue
        }

        return sources[selectedIndex-1], nil
    }
}

// --- END OF FILE cli/cli.go ---
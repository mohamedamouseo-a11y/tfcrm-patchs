#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path("/var/www/TFCRM")
LAYOUT = ROOT / "client/src/components/CRMLayout.tsx"
APP = ROOT / "client/src/App.tsx"

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        if new in text:
            print(f"{label}=ALREADY_APPLIED")
            return text
        raise RuntimeError(f"{label}: expected source block not found")
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    print(f"{label}=PATCHED")
    return text.replace(old, new, 1)

def main():
    if not LAYOUT.exists() or not APP.exists():
        raise RuntimeError("Run from TFCRM server with /var/www/TFCRM present")

    layout = LAYOUT.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")

    layout = replace_once(
        layout,
        'const waGatewayHrefs = ["/wa-gateway", "/wa-gateway/accounts"];',
        'const waGatewayHrefs = ["/wa-gateway", "/wa-gateway/tara", "/wa-gateway/accounts"];',
        "WHATSAPP_ACTIVE_ROUTES"
    )

    old_full = '''                      {[
                        { href: "/wa-gateway", label: isRTL ? "المحادثات" : "Inbox", icon: <MessageCircle size={15} />, roles: ["Admin","SalesManager","SalesAgent","ColdSalesAgent","TechnicalAccountManager","ServiceAdvisor","PartsAgent","CrmFollowUp","MediaBuyer","AccountManager","AccountManagerLead","BusinessDeveloper"] },
                        { href: "/wa-gateway/accounts", label: isRTL ? "الحسابات و QR" : "Accounts & QR", icon: <QrCode size={15} />, roles: ["Admin"] },
                      ].filter(sub => isModerator ? !isModeratorBlockedRoute(sub.href) : sub.roles.includes(role)).map(sub => {'''
    new_full = '''                      {[
                        { href: "/wa-gateway", label: isRTL ? "المحادثات" : "Inbox", icon: <MessageCircle size={15} />, roles: ["Admin","SalesManager","SalesAgent","ColdSalesAgent","TechnicalAccountManager","ServiceAdvisor","PartsAgent","CrmFollowUp","MediaBuyer","AccountManager","AccountManagerLead","BusinessDeveloper"] },
                        { href: "/wa-gateway/tara", label: isRTL ? "تارا" : "Tara", icon: <Bot size={15} />, roles: ["Admin"] },
                        { href: "/wa-gateway/accounts", label: isRTL ? "الحسابات و QR" : "Accounts & QR", icon: <QrCode size={15} />, roles: ["Admin"] },
                      ].filter(sub => isModerator ? !isModeratorBlockedRoute(sub.href) : sub.roles.includes(role)).map(sub => {'''
    layout = replace_once(layout, old_full, new_full, "FULL_WHATSAPP_TARA_ITEM")

    old_collapsed = '''                      {[
                        { href: "/wa-gateway", icon: <MessageCircle size={15} />, roles: ["Admin","SalesManager","SalesAgent","ColdSalesAgent","TechnicalAccountManager","ServiceAdvisor","PartsAgent","CrmFollowUp","MediaBuyer","AccountManager","AccountManagerLead","BusinessDeveloper"] },
                        { href: "/wa-gateway/accounts", icon: <QrCode size={15} />, roles: ["Admin"] },
                      ].filter(sub => isModerator ? !isModeratorBlockedRoute(sub.href) : sub.roles.includes(role)).map(sub => {'''
    new_collapsed = '''                      {[
                        { href: "/wa-gateway", icon: <MessageCircle size={15} />, roles: ["Admin","SalesManager","SalesAgent","ColdSalesAgent","TechnicalAccountManager","ServiceAdvisor","PartsAgent","CrmFollowUp","MediaBuyer","AccountManager","AccountManagerLead","BusinessDeveloper"] },
                        { href: "/wa-gateway/tara", icon: <Bot size={15} />, roles: ["Admin"] },
                        { href: "/wa-gateway/accounts", icon: <QrCode size={15} />, roles: ["Admin"] },
                      ].filter(sub => isModerator ? !isModeratorBlockedRoute(sub.href) : sub.roles.includes(role)).map(sub => {'''
    layout = replace_once(layout, old_collapsed, new_collapsed, "COLLAPSED_WHATSAPP_TARA_ITEM")

    old_mini_wa = '''      if (collapsedGroup === "whatsapp") return [
        { href: "/wa-gateway", label: isRTL ? "المحادثات" : "Conversations", icon: <MessageCircle size={18} />, roles: ["Admin","SalesManager","SalesAgent","ColdSalesAgent","TechnicalAccountManager","ServiceAdvisor","PartsAgent","CrmFollowUp","MediaBuyer","AccountManager","AccountManagerLead","BusinessDeveloper"] },
        { href: "/wa-gateway/accounts", label: isRTL ? "الحسابات و QR" : "Accounts & QR", icon: <QrCode size={18} />, roles: ["Admin"] },
      ].filter(item => !isModerator && item.roles.includes(role));'''
    new_mini_wa = '''      if (collapsedGroup === "whatsapp") return [
        { href: "/wa-gateway", label: isRTL ? "المحادثات" : "Conversations", icon: <MessageCircle size={18} />, roles: ["Admin","SalesManager","SalesAgent","ColdSalesAgent","TechnicalAccountManager","ServiceAdvisor","PartsAgent","CrmFollowUp","MediaBuyer","AccountManager","AccountManagerLead","BusinessDeveloper"] },
        { href: "/wa-gateway/tara", label: isRTL ? "تارا" : "Tara", icon: <Bot size={18} />, roles: ["Admin"] },
        { href: "/wa-gateway/accounts", label: isRTL ? "الحسابات و QR" : "Accounts & QR", icon: <QrCode size={18} />, roles: ["Admin"] },
      ].filter(item => !isModerator && item.roles.includes(role));'''
    layout = replace_once(layout, old_mini_wa, new_mini_wa, "MINI_WHATSAPP_TARA_ITEM")

    layout = replace_once(
        layout,
        '"/wa-gateway", "/wa-gateway/accounts", "/tara", "/zaghloul",',
        '"/wa-gateway", "/wa-gateway/tara", "/wa-gateway/accounts", "/tara", "/zaghloul",',
        "GROUPED_HREFS"
    )

    old_detect = '''  const detectCollapsedGroup = (): "whatsapp" | "ai" | "sales" | "marketing" | "am" | "bd" | null => {
    if (location === "/wa-gateway" || location.startsWith("/wa-gateway/") || waGatewayOpen) return "whatsapp";
    if (["/tara", "/zaghloul"].some(h => location === h || location.startsWith(h + "/")) || aiStaffOpen) return "ai";'''
    new_detect = '''  const detectCollapsedGroup = (): "whatsapp" | "ai" | "sales" | "marketing" | "am" | "bd" | null => {
    if (location === "/wa-gateway" || location.startsWith("/wa-gateway/") || location === "/tara" || waGatewayOpen) return "whatsapp";
    if (location === "/zaghloul" || location.startsWith("/zaghloul/") || aiStaffOpen) return "ai";'''
    layout = replace_once(layout, old_detect, new_detect, "COLLAPSED_GROUP_ROUTING")

    old_ai_items = '''      if (collapsedGroup === "ai") return [
        { href: "/tara", label: isRTL ? "تارا" : "Tara", icon: <Bot size={18} />, roles: ["Admin", "Moderator"] },
        { href: "/zaghloul", label: isRTL ? "زغلول" : "Zaghloul", icon: <Send size={18} />, roles: ["Admin"] },
      ].filter(item => item.roles.includes(role) && (!isModerator || !isModeratorBlockedRoute(item.href)));'''
    new_ai_items = '''      if (collapsedGroup === "ai") return [
        { href: "/zaghloul", label: isRTL ? "زغلول" : "Zaghloul", icon: <Send size={18} />, roles: ["Admin"] },
      ].filter(item => item.roles.includes(role) && (!isModerator || !isModeratorBlockedRoute(item.href)));'''
    layout = replace_once(layout, old_ai_items, new_ai_items, "AI_GROUP_REMOVE_TARA_DUPLICATE")

    old_mini_group = '''              <MiniGroup id="ai" label={groupLabel.ai} icon={<Bot size={19} />} enabled={["Admin", "Moderator"].includes(role)} active={["/tara", "/zaghloul"].some(h => location === h || location.startsWith(h + "/"))} />'''
    new_mini_group = '''              <MiniGroup id="ai" label={groupLabel.ai} icon={<Bot size={19} />} enabled={role === "Admin"} active={location === "/zaghloul" || location.startsWith("/zaghloul/")} />'''
    layout = replace_once(layout, old_mini_group, new_mini_group, "MINI_AI_GROUP_ZAGHLOUL_ONLY")

    old_app = '''      <Route path="/wa-gateway/accounts" component={WAGatewayAccounts} />
      <Route path="/wa-gateway/settings" component={WAGatewaySettings} />
      <Route path="/wa-gateway" component={WAGatewayInbox} />
      <Route path="/tara" component={TaraAgentPage} />'''
    new_app = '''      <Route path="/wa-gateway/accounts" component={WAGatewayAccounts} />
      <Route path="/wa-gateway/settings" component={WAGatewaySettings} />
      <Route path="/wa-gateway/tara" component={TaraAgentPage} />
      <Route path="/wa-gateway" component={WAGatewayInbox} />
      <Route path="/tara" component={TaraAgentPage} />'''
    app = replace_once(app, old_app, new_app, "TARA_WA_GATEWAY_ROUTE_ALIAS")

    LAYOUT.write_text(layout, encoding="utf-8")
    APP.write_text(app, encoding="utf-8")

    print("MODIFIED_FILES=client/src/components/CRMLayout.tsx,client/src/App.tsx")
    print("RESULT=PASS")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("RESULT=FAIL")
        print(f"ERROR={e}")
        sys.exit(1)

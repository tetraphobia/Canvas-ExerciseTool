{
  description = "Canvas Exercise Grader";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: builtins.listToAttrs
        (map (s: { name = s; value = f s; }) systems);
    in {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python313.withPackages (ps: [ ps.requests ]);
        in {
          default = pkgs.mkShell {
            packages = [ python ];
          };
        });
    };
}
